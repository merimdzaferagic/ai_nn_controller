# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Agent-Controlled Decorator for AIC Applications.

This module provides the @agent_controlled decorator that allows MCP/agent tools
to communicate **through** an app's process() loop rather than bypassing it.

Unlike existing MCP control tools (which bypass process() via send_manual_control()),
agent-controlled operations go through the process loop, giving the handler access
to live measurements and the app's internal state.

Flow:
    Agent (MCP tool call) → push AgentRequest to queue → process() cycle picks it up
      → handler runs with (request, measurements) → response set → MCP returns result

Usage:
    from ai_nn_controller import agent_controlled

    @aic_app(name="SmartApp")
    class SmartApp(AicApp):
        read_measurements = {8: ["preamp_gain", "signal_power"]}
        control_functions = {8: ["SET_GAIN"]}

        # IMPORTANT: @classmethod must be ABOVE @agent_controlled
        @classmethod
        @agent_controlled(
            name="optimize_gain",
            description="Optimize gain based on a strategy",
            schema={
                "properties": {
                    "node_id": {"type": "integer"},
                    "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
                },
                "required": ["node_id", "strategy"]
            }
        )
        def handle_optimize_gain(cls, request, measurements):
            node_id = request["node_id"]
            current = measurements.get(node_id, [{}])[-1] or {}
            new_gain = current.get("preamp_gain", 15) + 2.0
            cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"target_gain": new_gain}}))
            return {"status": "applied", "new_gain": new_gain}
"""

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from ..config import vprint


@dataclass
class AgentRequest:
    """Represents a pending agent-controlled operation request.

    Created by the MCP handler, pushed to the app's agent_requests queue,
    and processed within the controller's execution loop alongside process().

    Attributes:
        request_id: Unique identifier for this request.
        operation_name: Name of the agent-controlled operation to invoke.
        arguments: Arguments passed from the MCP tool call.
        response: Set by the handler after processing; returned to the MCP caller.
        error: Set if the handler raises an exception.
        event: Threading event used to synchronize the MCP handler and the
            controller execution loop.
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    event: threading.Event = field(default_factory=threading.Event)


# Storage for agent operations per app class
# Structure: {app_name: {operation_name: {"handler": func, "description": str, "schema": dict}}}
_app_agent_operations: Dict[str, Dict[str, Dict[str, Any]]] = {}


def agent_controlled(name: str, description: str, schema: Dict[str, Any]):
    """
    Decorator to register a method as an agent-controlled operation.

    The decorated method will be callable via MCP tools, but instead of
    bypassing process(), the request is queued and executed within the
    controller's execution loop with access to live measurements.

    The handler receives two arguments:
        - request (dict): The MCP tool arguments.
        - measurements (dict): Current measurements from the process loop.

    It should return a dict that will be sent back as the MCP tool result.

    Args:
        name: Operation name (used as MCP tool suffix, e.g., "optimize_gain").
        description: Human-readable description for the MCP tool.
        schema: JSON Schema for the tool's input parameters (properties + required).

    Returns:
        Decorator function that marks the method with _agent_operations metadata.

    Example:
        # IMPORTANT: @classmethod must be ABOVE @agent_controlled
        @classmethod
        @agent_controlled(
            name="optimize_gain",
            description="Optimize gain based on a strategy",
            schema={
                "properties": {
                    "node_id": {"type": "integer"},
                    "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
                },
                "required": ["node_id", "strategy"]
            }
        )
        def handle_optimize_gain(cls, request, measurements):
            return {"status": "applied"}
    """
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_agent_operations'):
            func._agent_operations = {}
        func._agent_operations[name] = {
            "handler": func,
            "description": description,
            "schema": schema,
        }

        vprint(f"[AgentControlled] Registered operation '{name}'")
        return func

    return decorator


def register_app_agent_operations(app_class: type, app_name: str) -> None:
    """
    Scan an app class for @agent_controlled decorated methods and register them.

    This is called by the @aic_app decorator during class registration,
    mirroring the pattern used by register_app_validators.

    Args:
        app_class: The AIC application class to scan.
        app_name: The unique name of the application.
    """
    operations = {}

    # Scan all class attributes for agent_controlled decorations
    for attr_name in dir(app_class):
        try:
            attr = getattr(app_class, attr_name)

            if hasattr(attr, '_agent_operations'):
                for op_name, op_info in attr._agent_operations.items():
                    operations[op_name] = {
                        "handler": attr,
                        "description": op_info["description"],
                        "schema": op_info["schema"],
                    }
                    vprint(f"[AgentControlled] App '{app_name}': registered operation '{op_name}' (direct)")

            elif hasattr(attr, '__func__') and hasattr(attr.__func__, '_agent_operations'):
                for op_name, op_info in attr.__func__._agent_operations.items():
                    operations[op_name] = {
                        "handler": attr,
                        "description": op_info["description"],
                        "schema": op_info["schema"],
                    }
                    vprint(f"[AgentControlled] App '{app_name}': registered operation '{op_name}' (__func__)")

        except Exception as e:
            vprint(f"[AgentControlled] Warning: Could not inspect '{attr_name}': {e}")

    # Also check __dict__ directly for classmethods
    for attr_name, attr in app_class.__dict__.items():
        try:
            if isinstance(attr, classmethod):
                func = attr.__func__
                if hasattr(func, '_agent_operations'):
                    for op_name, op_info in func._agent_operations.items():
                        if op_name not in operations:
                            operations[op_name] = {
                                "handler": getattr(app_class, attr_name),
                                "description": op_info["description"],
                                "schema": op_info["schema"],
                            }
                            vprint(f"[AgentControlled] App '{app_name}': registered operation '{op_name}' (__dict__)")
            elif callable(attr) and hasattr(attr, '_agent_operations'):
                for op_name, op_info in attr._agent_operations.items():
                    if op_name not in operations:
                        operations[op_name] = {
                            "handler": attr,
                            "description": op_info["description"],
                            "schema": op_info["schema"],
                        }
                        vprint(f"[AgentControlled] App '{app_name}': registered operation '{op_name}' (callable)")
        except Exception:
            pass

    if operations:
        _app_agent_operations[app_name] = operations
        # Also store handlers on the class for use during execution
        if not hasattr(app_class, '_agent_handlers'):
            app_class._agent_handlers = {}
        app_class._agent_handlers = {
            op_name: info["handler"] for op_name, info in operations.items()
        }
        vprint(f"[AgentControlled] App '{app_name}': {len(operations)} operation(s) registered")
    else:
        vprint(f"[AgentControlled] App '{app_name}': no agent operations found")


def get_app_agent_operations(app_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all registered agent-controlled operations for an application.

    Args:
        app_name: Name of the AIC application.

    Returns:
        Dictionary mapping operation names to their metadata
        (handler, description, schema).
    """
    return _app_agent_operations.get(app_name, {})
