# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
FastAPI integration for MCP.

This module provides FastAPI routes that expose MCP functionality
via HTTP/SSE transport, allowing web-based AI agents to use the tools.
"""

import json
import asyncio
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from .tool_registry import MCPToolRegistry
from .server import MCPServer, MCPRequest


class ToolCallRequest(BaseModel):
    """Request model for tool calls."""
    name: str
    arguments: Dict[str, Any] = {}


class MCPMessageRequest(BaseModel):
    """Request model for MCP JSON-RPC messages."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


def create_mcp_router(server: Optional[MCPServer] = None) -> APIRouter:
    """
    Create a FastAPI router with MCP endpoints.

    Args:
        server: Optional MCPServer instance. If not provided, creates a new one.

    Returns:
        FastAPI APIRouter with MCP endpoints
    """
    router = APIRouter(prefix="/mcp", tags=["MCP"])

    if server is None:
        server = MCPServer(name="aic-controller", version="1.0.0")

    @router.get("/")
    async def mcp_info():
        """Get MCP server information."""
        stats = MCPToolRegistry.get_stats()
        return {
            "name": server.name,
            "version": server.version,
            "protocol": "MCP",
            "transport": "HTTP/SSE",
            "stats": stats
        }

    @router.get("/tools")
    async def list_tools():
        """
        List all available MCP tools.

        Returns a list of tool definitions in MCP format.
        """
        tools = MCPToolRegistry.list_tools()
        return {"tools": tools, "count": len(tools)}

    @router.get("/tools/{app_name}")
    async def list_tools_by_app(app_name: str):
        """
        List MCP tools for a specific app.

        Args:
            app_name: Name of the AIC app
        """
        tools = MCPToolRegistry.list_tools_by_app(app_name)
        if not tools:
            raise HTTPException(
                status_code=404,
                detail=f"No tools found for app '{app_name}'"
            )
        return {"app": app_name, "tools": tools, "count": len(tools)}

    @router.post("/tools/call")
    async def call_tool(request: ToolCallRequest):
        """
        Call an MCP tool.

        Args:
            request: Tool call request with name and arguments
        """
        result = await MCPToolRegistry.call_tool(request.name, request.arguments)

        if "error" in result and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    @router.post("/message")
    async def handle_mcp_message(request: MCPMessageRequest):
        """
        Handle a raw MCP JSON-RPC message.

        This endpoint accepts standard MCP protocol messages,
        enabling compatibility with MCP clients.
        """
        mcp_request = MCPRequest(
            jsonrpc=request.jsonrpc,
            id=request.id,
            method=request.method,
            params=request.params
        )

        response = await server.handle_request(mcp_request)
        return response.to_dict()

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        """
        Server-Sent Events endpoint for MCP.

        Provides real-time updates about tool executions
        and system state changes.
        """
        async def event_generator():
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'server': server.name})}\n\n"

            # Send available tools
            tools = MCPToolRegistry.list_tools()
            yield f"data: {json.dumps({'type': 'tools', 'tools': tools})}\n\n"

            # Keep connection alive
            while True:
                if await request.is_disconnected():
                    break
                # Send heartbeat every 30 seconds
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                await asyncio.sleep(30)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    @router.get("/schema/{tool_name}")
    async def get_tool_schema(tool_name: str):
        """
        Get the JSON schema for a specific tool.

        Args:
            tool_name: Name of the tool
        """
        tool = MCPToolRegistry.get_tool(tool_name)
        if not tool:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found"
            )

        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
            "app": tool.app_name,
            "type": tool.tool_type
        }

    return router


def get_openapi_tool_specs() -> Dict[str, Any]:
    """
    Generate OpenAPI-compatible tool specifications.

    This can be used to expose tools to AI systems that
    prefer OpenAPI/function-calling format over MCP.

    Returns:
        Dict with OpenAPI-style function definitions
    """
    tools = MCPToolRegistry.list_tools()
    functions = []

    for tool in tools:
        functions.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["inputSchema"]
        })

    return {"functions": functions}
