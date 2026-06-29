# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from collections import deque
import json
import os
import threading
import time
import uuid

import zmq

from .RegisterAicApp import RegisterAicApp
from .aic_setup import check_entropy
from .arbitration import CommandArbitrator
from .config import AicConfig, vprint
from .decorators.command_validator import validate_command
from .enums import *
from .helpers.Validator import Validator
from .managers.AicManager import AicManager
from .mcp.tool_generator import MCPToolGenerator
from .observability import structured_log
from .plugin_framework import PluginManager, load_plugin_entrypoints, validate_app_plugins
from .plugins import CapabilityMetadata, PluginRegistry, load_app_entrypoints
from .protocol import MessageEnvelope, decode_message, encode_message
from .registry import execute_command, has_command
from .safety import SafetyPolicyEngine


class AicController:
    def __init__(self, with_api: bool = False, api_host: str = "0.0.0.0", api_port: int = 8000, verbose: bool = False):
        AicConfig.set_verbose(verbose)
        self.verbose = verbose
        self.with_api = with_api
        self.api_host = api_host
        self.api_port = api_port

        self.max_queue_size = int(os.getenv("AIC_MAX_QUEUE_SIZE", "500"))
        self.stop_event = threading.Event()
        self.policy_engine = SafetyPolicyEngine()
        self.arbitrator = CommandArbitrator(strategy=os.getenv("AIC_ARBITRATION_STRATEGY", "last_write_wins"))

        self.aic_apps = []
        self.aic_app_instances = {}
        self.app_states = {}
        self.app_threads = {}
        self.subscribed_topics = set()
        self.topics = []
        self.message_queue = {}

        # Plugins must load before apps so required_plugins can be validated.
        load_plugin_entrypoints()
        load_app_entrypoints()

        # Refresh MCP control-tool schemas now that register_specific_commands()
        # has run. The @aic_app decorator generates tools at import time before
        # commands are registered, so schemas fall back to the generic
        # {node_id, payload} shape. Re-generating here replaces those fallbacks
        # with the real per-field schemas (amp_type, target_gain, etc.).
        for app_name, app_class in AicManager.aic_apps.items():
            MCPToolGenerator.refresh_control_tools(app_name, app_class, AicManager)

        AicManager.set_controller(self)
        for aic_app in AicManager.aic_apps.values():
            Validator.validate_aic_app(aic_app)
            validate_app_plugins(aic_app)

        # Connect every loaded plugin now that validation passed.
        for plugin_name, plugin_class in PluginManager.all_plugins().items():
            try:
                plugin_class.connect()
            except Exception as exc:
                vprint(f"[AicController] Plugin '{plugin_name}' connect() failed: {exc}")

        PluginRegistry.register(CapabilityMetadata(
            name="AicController",
            plugin_type="controller",
            capabilities=["v2"],
            extra={"max_queue": self.max_queue_size},
        ))

        # Register each loaded plugin in the capability catalogue.
        for plugin_name, plugin_class in PluginManager.all_plugins().items():
            PluginRegistry.register(CapabilityMetadata(
                name=plugin_name,
                plugin_type="plugin",
                capabilities=[],
                extra={"plugin_type": getattr(plugin_class, "plugin_type", "generic")},
            ))

        register_aic_app_inst = RegisterAicApp()
        for aic_app in AicManager.aic_apps.values():
            register_aic_app_inst.register_aic_app(aic_app)

        broker_info = register_aic_app_inst.get_broker_info()
        databus_ip = broker_info["databus_ip"]
        listen_port = broker_info["listen_port"]
        command_port = broker_info["command_port"]

        self.sub_socket = f"tcp://{databus_ip}:{listen_port}"
        self.command_push_socket = f"tcp://{databus_ip}:{command_port}"

        check_entropy()
        self.connect()

    def connect(self):
        self.context = zmq.Context()
        self.consumer = self.context.socket(zmq.SUB)
        self.consumer.connect(self.sub_socket)
        self.consumer.setsockopt(zmq.LINGER, 0)
        self.consumer.setsockopt(zmq.RCVTIMEO, 1000)  # 1 s timeout so stop_event is checked

        self.command_pusher = self.context.socket(zmq.PUSH)
        self.command_pusher.connect(self.command_push_socket)
        time.sleep(0.2)

    def read_message(self):
        message_count = 0
        while not self.stop_event.is_set():
            try:
                message = self.consumer.recv().decode("utf-8")
                message_count += 1
                topic, payload = message.split(";", 1)
                read_topic = int(topic)

                decoded = decode_message(payload)
                body = decoded.get("payload", decoded) if isinstance(decoded, dict) else decoded
                correlation_id = decoded.get("correlation_id") if isinstance(decoded, dict) else None

                if read_topic in self.message_queue:
                    for aic_app_name in self.message_queue[read_topic]:
                        if self.app_states.get(aic_app_name) != "running":
                            continue
                        queue = self.message_queue[read_topic][aic_app_name]
                        if len(queue) >= self.max_queue_size:
                            queue.popleft()
                            structured_log("queue_backpressure_drop", level="WARN", topic=read_topic, app=aic_app_name)
                        queue.append(body)
                        if correlation_id:
                            structured_log("measurement_ingress", topic=read_topic, app=aic_app_name, correlation_id=correlation_id)
            except zmq.Again:
                continue  # RCVTIMEO expired — re-check stop_event
            except Exception as e:
                if not self.stop_event.is_set():
                    vprint(f"[READ_MESSAGE] Error: {e}")

    def send_command(self, node_id, command_payload, *, correlation_id=None, lineage_id=None, idempotency_key=None):
        if isinstance(command_payload, dict):
            payload = command_payload
        elif isinstance(command_payload, str):
            payload = json.loads(command_payload)
        else:
            payload = {"value": command_payload}

        effective_correlation_id = correlation_id or str(uuid.uuid4())
        envelope = MessageEnvelope(
            message_type="command",
            source="aic_controller",
            target=str(node_id),
            correlation_id=effective_correlation_id,
            lineage_id=lineage_id or "",
            idempotency_key=idempotency_key or "",
            payload=payload,
        )
        wire_payload = encode_message(envelope)
        message = f"{node_id};{wire_payload}"
        self.command_pusher.send_string(message)
        structured_log("command_egress", node_id=node_id, correlation_id=effective_correlation_id)

    def __aic_app_setup(self):
        for name, aic_app in AicManager.aic_apps.items():
            temp_aic_app = aic_app()
            self.aic_apps.append(temp_aic_app)
            self.aic_app_instances[name] = temp_aic_app
            self.app_states[name] = "stopped"
            for topic in temp_aic_app.cell_ids:
                self.topics.append(topic)
            control_functions = getattr(aic_app, "control_functions", {}) or {}
            command_capabilities = sorted({cmd for commands in control_functions.values() for cmd in commands})
            PluginRegistry.register(CapabilityMetadata(
                name=name,
                plugin_type="app",
                capabilities=command_capabilities,
                extra={"cell_ids": list(temp_aic_app.cell_ids)},
            ))
            # Inject live plugin references so process() can call cls.plugins["Name"]
            aic_app.plugins = {
                p: PluginManager.get(p)
                for p in getattr(aic_app, "required_plugins", [])
            }
        self.topics = list(set(self.topics))

    def _fail_pending_agent_requests(self, app_name: str, reason: str):
        app_class = AicManager.aic_apps.get(app_name)
        if not app_class or not hasattr(app_class, "agent_requests"):
            return 0

        failed = 0
        while app_class.agent_requests:
            request = app_class.agent_requests.popleft()
            request.error = reason
            request.event.set()
            failed += 1

        if failed:
            structured_log("agent_requests_drained", level="WARN", app=app_name, drained=failed, reason=reason)
        return failed

    def update_app_state(self, app_name: str, state: str):
        if app_name not in self.aic_app_instances:
            raise ValueError(f"Application {app_name} does not exist")

        old_state = self.app_states[app_name]
        if state == "running" and old_state == "stopped":
            self.app_states[app_name] = "running"
            thread = threading.Thread(target=self.__execute, args=[self.aic_app_instances[app_name]], daemon=True)
            thread.start()
            self.app_threads[app_name] = thread
        elif state in ("paused", "stopped", "running"):
            self.app_states[app_name] = state
            if state == "stopped":
                self._fail_pending_agent_requests(
                    app_name,
                    f"App '{app_name}' is stopped. Request cancelled.",
                )
        else:
            raise ValueError("Invalid state")
        return {"app": app_name, "state": state, "previous_state": old_state}

    def get_app_state(self, app_name: str):
        if app_name not in self.app_states:
            raise ValueError(f"Application {app_name} does not exist")
        return self.app_states[app_name]

    def get_app_measurements(self, app_name: str):
        if app_name not in self.aic_app_instances:
            raise ValueError(f"Application {app_name} does not exist")
        app = self.aic_app_instances[app_name]
        measurements = {}
        for topic in app.cell_ids:
            if topic in self.message_queue and app.u_name in self.message_queue[topic]:
                queue = self.message_queue[topic][app.u_name]
                measurements[topic] = queue[-1] if queue else None
        return measurements

    def send_manual_control(self, app_name: str, node_id: int, command: dict):
        if app_name not in self.aic_app_instances:
            raise ValueError(f"Application {app_name} does not exist")
        app = self.aic_app_instances[app_name]
        if node_id not in app.cell_ids:
            raise ValueError(f"Node {node_id} is not monitored by app {app_name}")

        cmd_name = command.get("command")
        cmd_payload = command.get("payload", {})
        app_class = AicManager.aic_apps.get(app_name)

        if cmd_name:
            validation_params = {"node_id": node_id, **cmd_payload}
            is_valid, error_msg = validate_command(app_name, app_class, cmd_name, validation_params)
            if not is_valid:
                return {"status": "rejected", "reason": error_msg, "command": command}

        allowed, reason = self.policy_engine.enforce(cmd_name or "unknown")
        if not allowed:
            return {"status": "rejected", "reason": reason, "command": command}
        allowed, reason = self.arbitrator.allow(node_id, cmd_name or "unknown", cmd_payload)
        if not allowed:
            return {"status": "rejected", "reason": reason, "command": command}

        if not cmd_name or not has_command(cmd_name):
            return {"status": "rejected", "reason": f"Unknown command: {cmd_name}", "command": command}

        node_payload = execute_command(cmd_name, node_id, cmd_payload)
        self.send_command(node_id, node_payload, correlation_id=str(uuid.uuid4()))
        return {"status": "sent", "command": {"command": cmd_name, "payload": cmd_payload}}

    def collect_measurements(self, aic_app):
        measurements = {}
        if aic_app.read_measurements:
            for topic in aic_app.cell_ids:
                if topic not in measurements:
                    measurements[topic] = []
                topic_measurements = aic_app.read_measurements.get(topic, [])
                queue = self.message_queue.get(topic, {}).get(aic_app.u_name)
                if queue is None:
                    continue
                while True:
                    try:
                        msg = queue.popleft()
                    except IndexError:
                        break
                    if MeasurementsHandler.ALL_MEASUREMENTS in topic_measurements:
                        measurements[topic].append(dict(msg.items()))
                    else:
                        filtered = dict(filter(lambda elem: elem[0] in topic_measurements, msg.items()))
                        measurements[topic].append(filtered)
        return measurements

    def process_commands(self, aic_app):
        app_class = AicManager.aic_apps.get(aic_app.u_name)
        while aic_app.send_commands:
            command = aic_app.send_commands.popleft()
            cmd_name = command[0]
            cmd_data = command[1]
            if not (isinstance(cmd_data, dict) and "node_id" in cmd_data):
                continue
            node_id = cmd_data.get("node_id")
            value = cmd_data.get("value", {})
            cmd_name_str = cmd_name if isinstance(cmd_name, str) else (cmd_name.name if hasattr(cmd_name, "name") else str(cmd_name))

            is_valid, error_msg = validate_command(aic_app.u_name, app_class, cmd_name_str, {"node_id": node_id, **value})
            if not is_valid:
                continue
            allowed, _ = self.policy_engine.enforce(cmd_name_str)
            if not allowed:
                continue
            allowed, _ = self.arbitrator.allow(node_id, cmd_name_str, value)
            if not allowed:
                continue

            if has_command(cmd_name_str):
                payload = execute_command(cmd_name_str, node_id, value)
                self.send_command(node_id, payload, correlation_id=str(uuid.uuid4()))

    def process_agent_requests(self, aic_app, measurements):
        app_class = AicManager.aic_apps.get(aic_app.u_name)
        if not app_class or not hasattr(app_class, "agent_requests"):
            return

        if self.app_states.get(aic_app.u_name) != "running":
            self._fail_pending_agent_requests(
                aic_app.u_name,
                f"App '{aic_app.u_name}' is stopped. Request cancelled.",
            )
            return

        while app_class.agent_requests:
            request = app_class.agent_requests.popleft()
            try:
                handlers = getattr(app_class, "_agent_handlers", {})
                handler = handlers.get(request.operation_name)
                if handler is None:
                    request.error = f"No handler found for operation {request.operation_name}"
                else:
                    request.response = handler(request.arguments, measurements)
            except Exception as e:
                request.error = str(e)
            finally:
                request.event.set()

    def __set_topics(self):
        for topic in self.topics:
            self.consumer.setsockopt(zmq.SUBSCRIBE, b"%d" % topic)
            self.message_queue[topic] = {}
            for aic_app in self.aic_apps:
                if topic in aic_app.cell_ids:
                    self.message_queue[topic][aic_app.u_name] = deque(maxlen=self.max_queue_size)

    def __execute(self, aic_app):
        while not self.stop_event.is_set():
            app_state = self.app_states.get(aic_app.u_name, "stopped")
            if app_state == "stopped":
                self._fail_pending_agent_requests(
                    aic_app.u_name,
                    f"App '{aic_app.u_name}' is stopped. Request cancelled.",
                )
                break
            if app_state == "paused":
                time.sleep(1)
                continue

            measurements = self.collect_measurements(aic_app)
            aic_app.process(measurements)
            self.process_agent_requests(aic_app, measurements)
            self.process_commands(aic_app)
            time.sleep(aic_app.control_loop_update_time)

    def discover_capabilities(self):
        return PluginRegistry.discover()

    def run(self):
        if self.with_api:
            self._run_with_api()
        else:
            self._run_controller_only()

    def _run_controller_only(self):
        self.__aic_app_setup()
        self.__set_topics()
        threading.Thread(target=self.read_message, daemon=True).start()
        while not self.stop_event.is_set():
            time.sleep(1)

    def _run_with_api(self):
        from .server import create_app
        import uvicorn
        app = create_app(self)
        uvicorn.run(app, host=self.api_host, port=self.api_port)

    def shutdown(self):
        self.stop_event.set()
        for plugin_name, plugin_class in PluginManager.all_plugins().items():
            try:
                plugin_class.disconnect()
            except Exception as exc:
                vprint(f"[AicController] Plugin '{plugin_name}' disconnect() error: {exc}")
        try:
            if hasattr(self, "consumer"):
                self.consumer.close(0)
            if hasattr(self, "command_pusher"):
                self.command_pusher.close(0)
            if hasattr(self, "context"):
                self.context.term()
        except Exception as exc:
            vprint(f"[AicController] Shutdown cleanup error: {exc}")
