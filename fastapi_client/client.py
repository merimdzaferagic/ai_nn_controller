# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
FastAPI Client for AIC Application Controller

This module provides a Python client interface for interacting with the
AIC Controller FastAPI server. It includes functions for:
- Managing app states (start, stop, pause, resume)
- Fetching measurements from apps
- Sending control commands to nodes
- Querying app information
- MCP (Model Context Protocol) tool discovery and execution

Usage:
    from fastapi_client import AicApiClient

    client = AicApiClient(base_url="http://aic_server:8000")

    # List all apps
    apps = client.list_apps()

    # Start an app
    client.start_app("NetworkControlApp")

    # Get measurements
    measurements = client.get_measurements("NetworkControlApp")

    # Send control command
    client.send_control("NetworkControlApp", 8, "SET_GAIN",
                       {"amp_type": "preamp", "target_gain": 12})

    # MCP Usage - discover and call tools:
    tools = client.mcp_list_tools()
    result = client.mcp_call_tool("NetworkControlApp_set_gain",
                                   {"node_id": 8, "target_gain": 15})

    # Or use convenience methods:
    result = client.mcp_set_gain("NetworkControlApp", node_id=8, target_gain=15)
"""

import requests
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time


@dataclass
class AppInfo:
    """Data class for application information."""
    name: str
    state: str
    node_id: int
    cell_ids: List[int]
    time_interval: int


@dataclass
class MCPTool:
    """Data class for MCP tool information."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    app_name: Optional[str] = None
    tool_type: Optional[str] = None

    @property
    def required_params(self) -> List[str]:
        """Get list of required parameters."""
        return self.input_schema.get("required", [])

    @property
    def parameters(self) -> Dict[str, Any]:
        """Get parameter definitions."""
        return self.input_schema.get("properties", {})


class AicApiClient:
    """
    Client for interacting with the AIC Controller FastAPI server.

    This client provides convenient methods for managing aic_app instances,
    fetching measurements, and sending control commands.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        """
        Initialize the AIC API client.

        Args:
            base_url: Base URL of the FastAPI server (default: http://localhost:8000)
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[API Error] {method} {url}: {e}")
            raise

    # ==================== Health & Info ====================

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the API server.

        Returns:
            Health status information
        """
        return self._make_request('GET', '/health')

    def get_api_info(self) -> Dict[str, Any]:
        """
        Get API information and available endpoints.

        Returns:
            API information dictionary
        """
        return self._make_request('GET', '/')

    # ==================== App Management ====================

    def list_apps(self) -> List[AppInfo]:
        """
        List all registered aic_app instances.

        Returns:
            List of AppInfo objects
        """
        response = self._make_request('GET', '/apps')
        apps = response.get('apps', [])
        return [AppInfo(**app) for app in apps]

    def get_app_info(self, app_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific app.

        Args:
            app_name: Name of the application

        Returns:
            App configuration details
        """
        return self._make_request('GET', f'/apps/{app_name}/info')

    def get_app_state(self, app_name: str) -> str:
        """
        Get the current state of an app.

        Args:
            app_name: Name of the application

        Returns:
            Current state (stopped, running, or paused)
        """
        response = self._make_request('GET', f'/apps/{app_name}/state')
        return response.get('state', 'unknown')

    def set_app_state(self, app_name: str, state: str) -> Dict[str, Any]:
        """
        Set the state of an app.

        Args:
            app_name: Name of the application
            state: Target state (stopped, running, or paused)

        Returns:
            State transition result
        """
        return self._make_request(
            'PUT',
            f'/apps/{app_name}/state',
            json={'state': state}
        )

    def start_app(self, app_name: str) -> Dict[str, Any]:
        """
        Start an app (transition to running state).

        Args:
            app_name: Name of the application

        Returns:
            State transition result
        """
        return self.set_app_state(app_name, 'running')

    def stop_app(self, app_name: str) -> Dict[str, Any]:
        """
        Stop an app (transition to stopped state).

        Args:
            app_name: Name of the application

        Returns:
            State transition result
        """
        return self.set_app_state(app_name, 'stopped')

    def pause_app(self, app_name: str) -> Dict[str, Any]:
        """
        Pause an app (transition to paused state).

        Args:
            app_name: Name of the application

        Returns:
            State transition result
        """
        return self.set_app_state(app_name, 'paused')

    def resume_app(self, app_name: str) -> Dict[str, Any]:
        """
        Resume a paused app (transition to running state).

        Args:
            app_name: Name of the application

        Returns:
            State transition result
        """
        return self.set_app_state(app_name, 'running')

    # ==================== Measurements ====================

    def get_measurements(self, app_name: str) -> Dict[int, Dict[str, Any]]:
        """
        Get the latest measurements for an app.

        Args:
            app_name: Name of the application

        Returns:
            Dictionary mapping node_id to measurement data
        """
        response = self._make_request('GET', f'/apps/{app_name}/measurements')
        return response.get('measurements', {})

    def get_node_measurement(self, app_name: str, node_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the latest measurement for a specific node.

        Args:
            app_name: Name of the application
            node_id: Node ID to get measurements for

        Returns:
            Measurement data for the node, or None if not available
        """
        measurements = self.get_measurements(app_name)
        return measurements.get(node_id)

    # ==================== Control Commands ====================

    def send_control(self, app_name: str, node_id: int, command: str,
                    payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a control command to a node via an app.

        Args:
            app_name: Name of the application
            node_id: Target node ID
            command: Command type (e.g., "SET_GAIN")
            payload: Command payload dictionary

        Returns:
            Command execution result
        """
        return self._make_request(
            'POST',
            f'/apps/{app_name}/control',
            json={
                'node_id': node_id,
                'command': command,
                'payload': payload
            }
        )

    # ==================== Convenience Methods ====================

    def wait_for_state(self, app_name: str, expected_state: str,
                       timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """
        Wait for an app to reach a specific state.

        Args:
            app_name: Name of the application
            expected_state: Expected state to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Time between state checks in seconds

        Returns:
            True if state reached, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_state = self.get_app_state(app_name)
                if current_state == expected_state:
                    return True
            except Exception as e:
                print(f"[Wait] Error checking state: {e}")
            time.sleep(poll_interval)
        return False

    def start_app_and_wait(self, app_name: str, timeout: int = 30) -> bool:
        """
        Start an app and wait for it to reach running state.

        Args:
            app_name: Name of the application
            timeout: Maximum time to wait in seconds

        Returns:
            True if app started successfully, False otherwise
        """
        self.start_app(app_name)
        return self.wait_for_state(app_name, 'running', timeout)

    def print_app_status(self, app_name: str):
        """
        Print detailed status information for an app.

        Args:
            app_name: Name of the application
        """
        print(f"\n{'='*70}")
        print(f"  Status for {app_name}")
        print(f"{'='*70}")

        try:
            # Get state
            state = self.get_app_state(app_name)
            print(f"State: {state}")

            # Get info
            info = self.get_app_info(app_name)
            print(f"Node ID: {info.get('node_id')}")
            print(f"Cell IDs: {info.get('cell_ids')}")
            print(f"Time Interval: {info.get('time_interval')}s")

            # Get measurements
            measurements = self.get_measurements(app_name)
            print(f"\nMeasurements from {len(measurements)} nodes:")
            for node_id, data in measurements.items():
                print(f"  Node {node_id}: {data}")

        except Exception as e:
            print(f"Error: {e}")

        print(f"{'='*70}\n")

    # ==================== MCP Tool Discovery ====================

    def mcp_get_info(self) -> Dict[str, Any]:
        """
        Get MCP server information.

        Returns:
            MCP server info including name, version, and statistics
        """
        return self._make_request('GET', '/mcp/')

    def mcp_list_tools(self) -> List[MCPTool]:
        """
        List all available MCP tools.

        Returns:
            List of MCPTool objects with tool definitions
        """
        response = self._make_request('GET', '/mcp/tools')
        tools = response.get('tools', [])
        return [
            MCPTool(
                name=t['name'],
                description=t['description'],
                input_schema=t['inputSchema']
            )
            for t in tools
        ]

    def mcp_list_tools_by_app(self, app_name: str) -> List[MCPTool]:
        """
        List MCP tools for a specific app.

        Args:
            app_name: Name of the application

        Returns:
            List of MCPTool objects for the specified app
        """
        response = self._make_request('GET', f'/mcp/tools/{app_name}')
        tools = response.get('tools', [])
        return [
            MCPTool(
                name=t['name'],
                description=t['description'],
                input_schema=t['inputSchema'],
                app_name=app_name
            )
            for t in tools
        ]

    def mcp_get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the full schema for a specific MCP tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema including name, description, inputSchema, app, and type
        """
        return self._make_request('GET', f'/mcp/schema/{tool_name}')

    def mcp_get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """
        Get a specific MCP tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            MCPTool object or None if not found
        """
        try:
            schema = self.mcp_get_tool_schema(tool_name)
            return MCPTool(
                name=schema['name'],
                description=schema['description'],
                input_schema=schema['inputSchema'],
                app_name=schema.get('app'),
                tool_type=schema.get('type')
            )
        except requests.exceptions.HTTPError:
            return None

    # ==================== MCP Tool Execution ====================

    def mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool with the given arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result
        """
        return self._make_request(
            'POST',
            '/mcp/tools/call',
            json={
                'name': tool_name,
                'arguments': arguments or {}
            }
        )

    def mcp_send_message(self, method: str, params: Dict[str, Any] = None,
                         request_id: int = None) -> Dict[str, Any]:
        """
        Send a raw MCP JSON-RPC message.

        Args:
            method: MCP method name (e.g., "tools/list", "tools/call")
            params: Method parameters
            request_id: Optional request ID

        Returns:
            MCP JSON-RPC response
        """
        message = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {}
        }
        if request_id is not None:
            message['id'] = request_id

        return self._make_request('POST', '/mcp/message', json=message)

    # ==================== MCP Convenience Methods ====================

    def mcp_set_gain(self, app_name: str, node_id: int, target_gain: float,
                     amp_type: str = "line") -> Dict[str, Any]:
        """
        Set amplifier gain using MCP tool.

        Args:
            app_name: Name of the application
            node_id: Target node ID
            target_gain: Target gain value in dB
            amp_type: Amplifier type ("line", "preamp", or "booster")

        Returns:
            Tool execution result
        """
        tool_name = f"{app_name}_set_gain"
        return self.mcp_call_tool(tool_name, {
            'node_id': node_id,
            'target_gain': target_gain,
            'amp_type': amp_type
        })

    def mcp_set_voa(self, app_name: str, node_id: int, channel: int,
                    attenuation: float, direction: str = "mux") -> Dict[str, Any]:
        """
        Set VOA attenuation using MCP tool.

        Args:
            app_name: Name of the application
            node_id: Target node ID
            channel: Channel number
            attenuation: Attenuation value in dB
            direction: VOA direction ("mux" or "demux")

        Returns:
            Tool execution result
        """
        tool_name = f"{app_name}_set_voa"
        return self.mcp_call_tool(tool_name, {
            'node_id': node_id,
            'channel': channel,
            'attenuation': attenuation,
            'direction': direction
        })

    def mcp_set_tilt(self, app_name: str, node_id: int,
                     tilt_value: float) -> Dict[str, Any]:
        """
        Set spectral tilt using MCP tool.

        Args:
            app_name: Name of the application
            node_id: Target node ID
            tilt_value: Tilt compensation value in dB

        Returns:
            Tool execution result
        """
        tool_name = f"{app_name}_set_tilt"
        return self.mcp_call_tool(tool_name, {
            'node_id': node_id,
            'tilt_value': tilt_value
        })

    def mcp_get_measurements(self, app_name: str,
                              node_id: int = None) -> Dict[str, Any]:
        """
        Get measurements using MCP tool.

        Args:
            app_name: Name of the application
            node_id: Optional node ID to filter measurements

        Returns:
            Measurement data
        """
        tool_name = f"{app_name}_get_measurements"
        arguments = {}
        if node_id is not None:
            arguments['node_id'] = node_id
        return self.mcp_call_tool(tool_name, arguments)

    def mcp_get_state(self, app_name: str) -> Dict[str, Any]:
        """
        Get app state using MCP tool.

        Args:
            app_name: Name of the application

        Returns:
            App state information
        """
        tool_name = f"{app_name}_get_state"
        return self.mcp_call_tool(tool_name, {})

    def mcp_set_state(self, app_name: str, state: str) -> Dict[str, Any]:
        """
        Set app state using MCP tool.

        Args:
            app_name: Name of the application
            state: Target state ("running", "paused", or "stopped")

        Returns:
            State transition result
        """
        tool_name = f"{app_name}_set_state"
        return self.mcp_call_tool(tool_name, {'state': state})

    def mcp_start_app(self, app_name: str) -> Dict[str, Any]:
        """Start an app using MCP tool."""
        return self.mcp_set_state(app_name, 'running')

    def mcp_stop_app(self, app_name: str) -> Dict[str, Any]:
        """Stop an app using MCP tool."""
        return self.mcp_set_state(app_name, 'stopped')

    def mcp_pause_app(self, app_name: str) -> Dict[str, Any]:
        """Pause an app using MCP tool."""
        return self.mcp_set_state(app_name, 'paused')

    # ==================== MCP Utility Methods ====================

    def mcp_print_tools(self, app_name: str = None):
        """
        Print available MCP tools in a formatted way.

        Args:
            app_name: Optional app name to filter tools
        """
        if app_name:
            tools = self.mcp_list_tools_by_app(app_name)
            print(f"\n{'='*70}")
            print(f"  MCP Tools for {app_name}")
            print(f"{'='*70}")
        else:
            tools = self.mcp_list_tools()
            print(f"\n{'='*70}")
            print(f"  All MCP Tools ({len(tools)} total)")
            print(f"{'='*70}")

        for tool in tools:
            print(f"\n  {tool.name}")
            print(f"    {tool.description}")
            if tool.required_params:
                print(f"    Required: {', '.join(tool.required_params)}")
            if tool.parameters:
                print(f"    Parameters:")
                for param, schema in tool.parameters.items():
                    param_type = schema.get('type', 'any')
                    desc = schema.get('description', '')
                    enum = schema.get('enum')
                    if enum:
                        print(f"      - {param}: {param_type} (options: {enum})")
                    else:
                        print(f"      - {param}: {param_type}")

        print(f"\n{'='*70}\n")

    def mcp_validate_tool_call(self, tool_name: str,
                                arguments: Dict[str, Any]) -> List[str]:
        """
        Validate arguments for a tool call before executing.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        tool = self.mcp_get_tool(tool_name)

        if not tool:
            return [f"Tool '{tool_name}' not found"]

        # Check required parameters
        for param in tool.required_params:
            if param not in arguments:
                errors.append(f"Missing required parameter: {param}")

        # Check parameter types and enums
        for param, value in arguments.items():
            if param in tool.parameters:
                schema = tool.parameters[param]

                # Check enum values
                if 'enum' in schema and value not in schema['enum']:
                    errors.append(
                        f"Invalid value for '{param}': {value}. "
                        f"Must be one of: {schema['enum']}"
                    )

                # Basic type checking
                expected_type = schema.get('type')
                if expected_type == 'integer' and not isinstance(value, int):
                    errors.append(f"Parameter '{param}' must be an integer")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Parameter '{param}' must be a number")
                elif expected_type == 'string' and not isinstance(value, str):
                    errors.append(f"Parameter '{param}' must be a string")

        return errors

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()


# Convenience functions for quick operations
def create_client(base_url: str = "http://localhost:8000") -> AicApiClient:
    """Create and return an AIC API client."""
    return AicApiClient(base_url)
