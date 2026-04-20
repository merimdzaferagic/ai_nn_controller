# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
MCP Server Implementation for the AIC Framework.

This module provides an MCP server that exposes auto-generated tools
to AI agents via the Model Context Protocol.

Supports both stdio transport (for Claude Desktop, etc.) and
can be integrated with FastAPI for HTTP/SSE transport.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .tool_registry import MCPToolRegistry
from ..config import vprint


@dataclass
class MCPRequest:
    """Represents an MCP protocol request."""
    jsonrpc: str
    id: Optional[int]
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class MCPResponse:
    """Represents an MCP protocol response."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        response = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response["id"] = self.id
        if self.error is not None:
            response["error"] = self.error
        elif self.result is not None:
            response["result"] = self.result
        return response


class MCPServer:
    """
    MCP Server that exposes AIC tools to AI agents.

    This server implements the Model Context Protocol and automatically
    exposes all tools registered in the MCPToolRegistry.
    """

    def __init__(self, name: str = "aic-controller", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._initialized = False

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an MCP protocol request.

        Args:
            request: The MCP request to handle

        Returns:
            MCPResponse with the result or error
        """
        method_handlers = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "ping": self._handle_ping,
        }

        handler = method_handlers.get(request.method)
        if handler is None:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )

        try:
            result = await handler(request.params or {})
            return MCPResponse(id=request.id, result=result)
        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": str(e)
                }
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the initialize request."""
        self._initialized = True
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }

    async def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle the initialized notification."""
        return None

    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        return {}

    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = MCPToolRegistry.list_tools()
        return {"tools": tools}

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        result = await MCPToolRegistry.call_tool(tool_name, arguments)

        # Format result as MCP content
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }


class StdioMCPServer(MCPServer):
    """
    MCP Server with stdio transport.

    This server reads JSON-RPC requests from stdin and writes
    responses to stdout, compatible with Claude Desktop and
    other MCP clients.
    """

    async def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        vprint(f"[MCP Server] Starting {self.name} v{self.version}")
        vprint(f"[MCP Server] Registered tools: {len(MCPToolRegistry.list_tools())}")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                # Read a line from stdin
                line = await reader.readline()
                if not line:
                    break

                line = line.decode('utf-8').strip()
                if not line:
                    continue

                # Parse the JSON-RPC request
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    error_response = MCPResponse(
                        error={"code": -32700, "message": f"Parse error: {e}"}
                    )
                    self._write_response(error_response)
                    continue

                # Handle the request
                request = MCPRequest(
                    jsonrpc=data.get("jsonrpc", "2.0"),
                    id=data.get("id"),
                    method=data.get("method", ""),
                    params=data.get("params")
                )

                response = await self.handle_request(request)

                # Only send response if there's an id (not a notification)
                if request.id is not None:
                    self._write_response(response)

            except Exception as e:
                vprint(f"[MCP Server] Error: {e}")
                error_response = MCPResponse(
                    error={"code": -32603, "message": str(e)}
                )
                self._write_response(error_response)

    def _write_response(self, response: MCPResponse):
        """Write a response to stdout."""
        response_json = json.dumps(response.to_dict())
        sys.stdout.write(response_json + "\n")
        sys.stdout.flush()


def create_mcp_server(name: str = "aic-controller", version: str = "1.0.0") -> MCPServer:
    """
    Factory function to create an MCP server.

    Args:
        name: Server name
        version: Server version

    Returns:
        MCPServer instance
    """
    return MCPServer(name=name, version=version)


def create_stdio_server(name: str = "aic-controller", version: str = "1.0.0") -> StdioMCPServer:
    """
    Factory function to create a stdio MCP server.

    Args:
        name: Server name
        version: Server version

    Returns:
        StdioMCPServer instance
    """
    return StdioMCPServer(name=name, version=version)
