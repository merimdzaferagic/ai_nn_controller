# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
MCP Tool Registry - Central registry for auto-generated MCP tools.

This module manages the collection of MCP tools that are automatically
generated from @aic_app decorated classes.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import json
from ..config import vprint


@dataclass
class MCPTool:
    """Represents a single MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable
    app_name: str
    tool_type: str  # "control", "measurement", "state"

    def to_mcp_format(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPToolRegistry:
    """
    Central registry for MCP tools generated from AIC apps.

    This is a singleton that collects tools as @aic_app decorators run,
    then exposes them via the MCP protocol.
    """

    _tools: Dict[str, MCPTool] = {}
    _apps_registered: List[str] = []
    _manager_ref = None  # Reference to AicManager for executing tools

    @classmethod
    def set_manager(cls, manager):
        """Set reference to AicManager for tool execution."""
        cls._manager_ref = manager

    @classmethod
    def register_tool(cls, tool: MCPTool) -> None:
        """
        Register an MCP tool.

        Args:
            tool: MCPTool instance to register
        """
        if tool.name in cls._tools:
            vprint(f"[MCPRegistry] Warning: Overwriting existing tool '{tool.name}'")

        cls._tools[tool.name] = tool
        vprint(f"[MCPRegistry] Registered tool: {tool.name}")

    @classmethod
    def register_app(cls, app_name: str) -> None:
        """Track that an app has been registered."""
        if app_name not in cls._apps_registered:
            cls._apps_registered.append(app_name)

    @classmethod
    def get_tool(cls, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """
        List all registered tools in MCP format.

        Returns:
            List of tool definitions in MCP protocol format
        """
        return [tool.to_mcp_format() for tool in cls._tools.values()]

    @classmethod
    def list_tools_by_app(cls, app_name: str) -> List[Dict[str, Any]]:
        """List tools for a specific app."""
        return [
            tool.to_mcp_format()
            for tool in cls._tools.values()
            if tool.app_name == app_name
        ]

    @classmethod
    def get_registered_apps(cls) -> List[str]:
        """Get list of app names that have registered tools."""
        return list(cls._apps_registered)

    @classmethod
    async def call_tool(cls, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        tool = cls._tools.get(name)
        if not tool:
            return {
                "error": f"Tool '{name}' not found",
                "available_tools": list(cls._tools.keys())
            }

        try:
            result = await tool.handler(arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def call_tool_sync(cls, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of call_tool for non-async contexts.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        tool = cls._tools.get(name)
        if not tool:
            return {
                "error": f"Tool '{name}' not found",
                "available_tools": list(cls._tools.keys())
            }

        try:
            # Handler might be sync or async - handle both
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(tool.handler):
                # Run async handler in event loop
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(tool.handler(arguments))
                finally:
                    loop.close()
            else:
                result = tool.handler(arguments)

            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools (useful for testing)."""
        cls._tools.clear()
        cls._apps_registered.clear()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get registry statistics."""
        tools_by_type = {"control": 0, "measurement": 0, "state": 0, "agent_controlled": 0}
        for tool in cls._tools.values():
            tools_by_type[tool.tool_type] = tools_by_type.get(tool.tool_type, 0) + 1

        return {
            "total_tools": len(cls._tools),
            "total_apps": len(cls._apps_registered),
            "apps": cls._apps_registered,
            "tools_by_type": tools_by_type,
            "tool_names": list(cls._tools.keys())
        }
