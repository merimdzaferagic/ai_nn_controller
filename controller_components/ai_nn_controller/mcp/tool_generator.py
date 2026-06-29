# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
MCP Tool Generator - Automatically generates MCP tools from @aic_app definitions.

This module inspects AicApp classes and generates corresponding MCP tools
based on their read_measurements and control_functions attributes.
"""

from typing import Dict, Any, List, Type, Callable
from .tool_registry import MCPToolRegistry, MCPTool
from ..registry import get_command_schema, get_command_description, get_measurement_schema, get_state_schema
from ..decorators.agent_controlled import get_app_agent_operations, AgentRequest


class MCPToolGenerator:
    """
    Generates MCP tools from AicApp class definitions.

    This class is used by the @aic_app decorator to automatically create
    MCP tool definitions based on the app's declared capabilities.
    """

    @classmethod
    def generate_tools_for_app(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> List[MCPTool]:
        """
        Generate all MCP tools for an AIC app.

        Args:
            app_name: Name of the app
            app_class: The AicApp subclass
            manager_class: Reference to AicManager for creating handlers

        Returns:
            List of generated MCPTool instances
        """
        tools = []

        # Generate control tools from control_functions
        control_tools = cls._generate_control_tools(app_name, app_class, manager_class)
        tools.extend(control_tools)

        # Generate measurement tool if app has read_measurements
        if hasattr(app_class, 'read_measurements') and app_class.read_measurements:
            measurement_tool = cls._generate_measurement_tool(app_name, app_class, manager_class)
            tools.append(measurement_tool)

        # Generate state management tools
        state_tools = cls._generate_state_tools(app_name, app_class, manager_class)
        tools.extend(state_tools)

        # Generate agent-controlled tools
        agent_tools = cls._generate_agent_tools(app_name, app_class, manager_class)
        tools.extend(agent_tools)

        # Register app
        MCPToolRegistry.register_app(app_name)

        # Register all tools
        for tool in tools:
            MCPToolRegistry.register_tool(tool)

        return tools

    @classmethod
    def _generate_control_tools(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> List[MCPTool]:
        """Generate MCP tools for control functions."""
        tools = []

        control_functions = getattr(app_class, 'control_functions', {})
        if not control_functions:
            return tools

        # Collect all commands and their allowed nodes
        commands_to_nodes: Dict[str, List[int]] = {}
        for node_id, commands in control_functions.items():
            for cmd in commands:
                if cmd not in commands_to_nodes:
                    commands_to_nodes[cmd] = []
                commands_to_nodes[cmd].append(node_id)

        # Create a tool for each command type
        for cmd_name, node_ids in commands_to_nodes.items():
            tool_name = f"{app_name}_{cmd_name.lower()}"
            schema = get_command_schema(cmd_name, node_ids)

            # Get description from registry
            base_description = get_command_description(cmd_name)
            description = f"{base_description}. App: {app_name}, Nodes: {node_ids}"

            # Create handler that routes to AicManager
            handler = cls._create_control_handler(app_name, cmd_name, manager_class)

            tool = MCPTool(
                name=tool_name,
                description=description,
                input_schema=schema,
                handler=handler,
                app_name=app_name,
                tool_type="control"
            )
            tools.append(tool)

        return tools

    @classmethod
    def _generate_measurement_tool(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> MCPTool:
        """Generate MCP tool for reading measurements."""
        read_measurements = getattr(app_class, 'read_measurements', {})
        node_ids = list(read_measurements.keys())

        tool_name = f"{app_name}_get_measurements"
        schema = get_measurement_schema(node_ids, read_measurements)

        # Build description with available measurements
        measurement_info = []
        for node_id, metrics in read_measurements.items():
            measurement_info.append(f"Node {node_id}: {', '.join(metrics[:3])}{'...' if len(metrics) > 3 else ''}")

        description = (
            f"Get current measurements from nodes monitored by {app_name}. "
            f"Available: {'; '.join(measurement_info[:3])}"
        )

        handler = cls._create_measurement_handler(app_name, manager_class)

        return MCPTool(
            name=tool_name,
            description=description,
            input_schema=schema,
            handler=handler,
            app_name=app_name,
            tool_type="measurement"
        )

    @classmethod
    def _generate_state_tools(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> List[MCPTool]:
        """Generate MCP tools for app state management."""
        tools = []

        # Get state tool
        get_state_tool = MCPTool(
            name=f"{app_name}_get_state",
            description=f"Get the current state of {app_name} (running, paused, or stopped)",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=cls._create_get_state_handler(app_name, manager_class),
            app_name=app_name,
            tool_type="state"
        )
        tools.append(get_state_tool)

        # Set state tool
        set_state_tool = MCPTool(
            name=f"{app_name}_set_state",
            description=f"Set the state of {app_name}. Use 'running' to start, 'paused' to pause, 'stopped' to stop.",
            input_schema=get_state_schema(),
            handler=cls._create_set_state_handler(app_name, manager_class),
            app_name=app_name,
            tool_type="state"
        )
        tools.append(set_state_tool)

        return tools

    @classmethod
    def _create_control_handler(
        cls,
        app_name: str,
        command_name: str,
        manager_class: Type
    ) -> Callable:
        """Create a handler function for a control command."""

        async def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            node_id = arguments.get("node_id")
            if node_id is None:
                return {"error": "node_id is required"}

            # Build payload from arguments (excluding node_id)
            payload = {k: v for k, v in arguments.items() if k != "node_id"}

            # Route through AicManager
            try:
                result = manager_class.send_manual_control(
                    app_name,
                    node_id,
                    {"command": command_name, "payload": payload}
                )
                return result
            except Exception as e:
                return {"error": str(e)}

        return handler

    @classmethod
    def _create_measurement_handler(
        cls,
        app_name: str,
        manager_class: Type
    ) -> Callable:
        """Create a handler function for getting measurements."""

        async def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            try:
                measurements = manager_class.get_measurements(app_name)
                node_id = arguments.get("node_id")

                if node_id is not None:
                    # Filter to specific node
                    if node_id in measurements:
                        return {"node_id": node_id, "measurements": measurements[node_id]}
                    else:
                        return {"error": f"No measurements for node {node_id}"}

                return {"measurements": measurements}
            except Exception as e:
                return {"error": str(e)}

        return handler

    @classmethod
    def _create_get_state_handler(
        cls,
        app_name: str,
        manager_class: Type
    ) -> Callable:
        """Create a handler function for getting app state."""

        async def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            try:
                state = manager_class.get_app_state(app_name)
                return {"app": app_name, "state": state}
            except Exception as e:
                return {"error": str(e)}

        return handler

    @classmethod
    def _create_set_state_handler(
        cls,
        app_name: str,
        manager_class: Type
    ) -> Callable:
        """Create a handler function for setting app state."""

        async def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            state = arguments.get("state")
            if not state:
                return {"error": "state is required"}

            if state not in ["running", "paused", "stopped"]:
                return {"error": f"Invalid state '{state}'. Must be: running, paused, stopped"}

            try:
                result = manager_class.update_state(app_name, state)
                return result
            except Exception as e:
                return {"error": str(e)}

        return handler

    @classmethod
    def refresh_control_tools(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> None:
        """Re-generate control tool schemas after commands have been registered.

        Called by AicController after load_app_entrypoints() so the real
        command schemas (amp_type, target_gain, etc.) replace the generic
        fallback schemas that were baked in at @aic_app decoration time.
        """
        for tool in cls._generate_control_tools(app_name, app_class, manager_class):
            MCPToolRegistry.register_tool(tool)

    @classmethod
    def _generate_agent_tools(
        cls,
        app_name: str,
        app_class: Type,
        manager_class: Type
    ) -> List[MCPTool]:
        """Generate MCP tools for @agent_controlled operations."""
        tools = []

        operations = get_app_agent_operations(app_name)
        if not operations:
            return tools

        for op_name, op_info in operations.items():
            tool_name = f"{app_name}_{op_name}"

            # Build full JSON Schema from the user-provided schema fragment
            schema = {
                "type": "object",
                **op_info["schema"]
            }

            description = f"{op_info['description']}. App: {app_name} (runs inside process loop)"

            handler = cls._create_agent_handler(
                app_name, op_name, app_class, manager_class
            )

            tool = MCPTool(
                name=tool_name,
                description=description,
                input_schema=schema,
                handler=handler,
                app_name=app_name,
                tool_type="agent_controlled"
            )
            tools.append(tool)

        return tools

    @classmethod
    def _create_agent_handler(
        cls,
        app_name: str,
        operation_name: str,
        app_class: Type,
        manager_class: Type
    ) -> Callable:
        """Create an async handler for an agent-controlled operation.

        The handler pushes an AgentRequest to the app's queue and waits
        for the controller's execution loop to process it.
        """
        import asyncio

        async def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            # Check app state first
            try:
                state = manager_class.get_app_state(app_name)
                if state != "running":
                    return {
                        "error": f"App '{app_name}' is not running (state: {state}). "
                                 f"Start the app first."
                    }
            except Exception as e:
                return {"error": f"Cannot check app state: {str(e)}"}

            # Create the request
            request = AgentRequest(
                operation_name=operation_name,
                arguments=arguments,
            )

            # Push to the app's queue
            app_class.agent_requests.append(request)

            # Fail-fast if the app transitioned away from running between
            # the pre-check and queue append.
            try:
                state_after_enqueue = manager_class.get_app_state(app_name)
            except Exception as e:
                try:
                    app_class.agent_requests.remove(request)
                except ValueError:
                    pass
                request.error = f"Cannot verify app state after enqueue: {str(e)}"
                request.event.set()
                return {"error": request.error, "request_id": request.request_id}

            if state_after_enqueue != "running":
                try:
                    app_class.agent_requests.remove(request)
                except ValueError:
                    pass
                request.error = (
                    f"App '{app_name}' is stopped. Request cancelled "
                    f"(state: {state_after_enqueue})."
                )
                request.event.set()

            # Calculate timeout: control_loop_update_time * 3 + 5 seconds
            timeout = getattr(app_class, 'control_loop_update_time', 1) * 3 + 5

            # Wait for the event (non-blocking for FastAPI via run_in_executor)
            loop = asyncio.get_event_loop()
            completed = await loop.run_in_executor(
                None, request.event.wait, timeout
            )

            if not completed:
                return {
                    "error": f"Timeout waiting for operation '{operation_name}' "
                             f"(request_id={request.request_id}, timeout={timeout}s). "
                             f"The app may be paused or the process loop is stalled."
                }

            if request.error:
                return {
                    "error": request.error,
                    "request_id": request.request_id
                }

            return {
                "result": request.response,
                "request_id": request.request_id
            }

        return handler
