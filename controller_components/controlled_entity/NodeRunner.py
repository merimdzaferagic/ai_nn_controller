# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

import json
import os
import signal
import threading
import time
import uuid
from collections import OrderedDict

import zmq

from . import messages
from .config import NodeConfig, vprint
from .decorators.node import get_registered_node
from .parse_config import parse_config


class NodeRunner:
    def __init__(self, config_file="./node.conf", verbose=False):
        NodeConfig.set_verbose(verbose)

        node_cls = get_registered_node()
        if node_cls is None:
            raise RuntimeError("No node class registered. Use @node decorator.")

        self.config = parse_config(config_file)
        self.node_id = int(self.config["node_id"])
        self.register_socket = f"tcp://{self.config['ip_address']}:{self.config['register_port']}"
        self.node = node_cls()
        self.node.config = self.config

        self.max_pending_commands = int(os.getenv("NODE_MAX_PENDING_COMMANDS", "200"))
        self.seen_idempotency = OrderedDict()
        self.stop_event = threading.Event()

        self.databus_ip = None
        self.send_pm_port = None
        self.command_port = None
        self.context = zmq.Context()
        self.alive_interval = 2

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self.stop_event.set()

    def _connect_to_register(self):
        self.registration_handle = self.context.socket(zmq.REQ)
        self.registration_handle.connect(self.register_socket)

    def _send_msg(self, msg):
        self.registration_handle.send(json.dumps(msg).encode("utf-8"))

    def _read_msg(self):
        recv_msg = self.registration_handle.recv()
        return json.loads(recv_msg.decode("utf-8"))

    def _register(self):
        msg = messages.register_node.copy()
        msg["node_id"] = self.node_id
        self._send_msg(msg)
        response = self._read_msg()
        if response.get("msg_type") == "err_msg":
            raise RuntimeError(f"Registration failed: {response.get('msg_content')}")

    def _register_pms(self):
        msg = messages.pm_availability.copy()
        msg["node_id"] = self.node_id
        msg["available_pms"] = self.node.available_measurements
        msg["capability_metadata"] = {
            "schema": "urn:ai-nnc:capability:1",
            "version": "1.0.0",
            "compatibility": {"min": "1.0.0", "max": "2.x"},
            "measurements": self.node.available_measurements,
        }
        self._send_msg(msg)
        response = self._read_msg()
        if response.get("msg_type") == "err_msg":
            raise RuntimeError(f"PM registration failed: {response.get('msg_content')}")

        self.databus_ip = response.get("databus_ip")
        self.send_pm_port = response.get("send_pm_port")
        self.command_port = response.get("recv_command_port")

    def _register_ctrls(self):
        if not self.node.available_controls:
            return
        msg = messages.ctrl_availability.copy()
        msg["node_id"] = self.node_id
        msg["available_ctrls"] = self.node.available_controls
        msg["capability_metadata"] = {
            "schema": "urn:ai-nnc:capability:1",
            "version": "1.0.0",
            "compatibility": {"min": "1.0.0", "max": "2.x"},
            "controls": self.node.available_controls,
        }
        self._send_msg(msg)
        response = self._read_msg()
        if response.get("msg_type") == "err_msg":
            raise RuntimeError(f"Ctrl registration failed: {response.get('msg_content')}")

    def _connect_to_databus(self):
        self.measurement_pusher = self.context.socket(zmq.PUSH)
        self.measurement_pusher.setsockopt(zmq.SNDHWM, self.max_pending_commands)
        self.measurement_pusher.connect(f"tcp://{self.databus_ip}:{self.send_pm_port}")

    def _setup_command_listener(self):
        if not self.node.available_controls or not self.command_port:
            return
        self.command_subscriber = self.context.socket(zmq.SUB)
        self.command_subscriber.setsockopt(zmq.RCVHWM, self.max_pending_commands)
        self.command_subscriber.connect(f"tcp://{self.databus_ip}:{self.command_port}")
        self.command_subscriber.setsockopt_string(zmq.SUBSCRIBE, str(self.node_id))

    def _send_alive(self):
        msg = messages.alive.copy()
        msg["node_id"] = self.node_id
        self._send_msg(msg)
        _ = self._read_msg()

    def _build_measurement_payload(self, measurements: dict) -> str:
        """Serialize a measurements dict to the v2 wire-format JSON string."""
        cid = str(uuid.uuid4())
        return json.dumps({
            "schema": "urn:ai-nnc:envelope:1",
            "version": "1.0",
            "message_type": "measurement",
            "source": str(self.node_id),
            "target": "controller",
            "correlation_id": cid,
            "lineage_id": cid,
            "idempotency_key": str(uuid.uuid4()),
            "ts": time.time(),
            "payload": measurements,
        })

    def _measurement_loop(self):
        while not self.stop_event.is_set():
            try:
                measurements = self.node.poll_measurements()
                if measurements is not None:
                    payload = self._build_measurement_payload(measurements)
                    self.measurement_pusher.send_string(f"{self.node_id};{payload}")
                time.sleep(self.node.measurement_interval)
            except Exception as e:
                print(f"[MEASUREMENTS] Error: {e}")
                time.sleep(self.node.measurement_interval)

    def _command_loop(self):
        while not self.stop_event.is_set():
            try:
                message = self.command_subscriber.recv_string()
                parts = message.split(";", 1)
                if len(parts) != 2:
                    continue
                payload = json.loads(parts[1])
                if isinstance(payload, dict) and payload.get("schema") == "urn:ai-nnc:envelope:1":
                    idem = payload.get("idempotency_key")
                    if idem and idem in self.seen_idempotency:
                        continue
                    if idem:
                        self.seen_idempotency[idem] = None
                        if len(self.seen_idempotency) > self.max_pending_commands:
                            self.seen_idempotency.popitem(last=False)
                    payload = payload.get("payload", {})
                self.node.handle_command(payload)
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[COMMAND] Error: {e}")

    def shutdown(self):
        self.stop_event.set()
        try:
            for attr in ["registration_handle", "measurement_pusher", "command_subscriber"]:
                sock = getattr(self, attr, None)
                if sock is not None:
                    sock.close(0)
            self.context.term()
        except Exception:
            pass

    def run(self):
        try:
            self._connect_to_register()
            self._register()
            self._register_pms()
            self._register_ctrls()
            self._connect_to_databus()
            self._setup_command_listener()
            self.node.setup()

            threading.Thread(target=self._measurement_loop, daemon=True).start()
            if self.node.available_controls and self.command_port:
                threading.Thread(target=self._command_loop, daemon=True).start()

            while not self.stop_event.is_set():
                time.sleep(self.alive_interval)
                self._send_alive()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
