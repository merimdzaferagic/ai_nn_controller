# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
FastAPI Client Package

This package provides a Python client for interacting with the AIC Controller FastAPI server.

Modules:
    client: Core API client implementation with MCP support
    examples: Example usage scripts
    cli: Interactive command-line interface

Usage:
    from fastapi_client.client import AicApiClient

    client = AicApiClient("http://localhost:8000")
    apps = client.list_apps()

    # MCP tool usage:
    tools = client.mcp_list_tools()
    result = client.mcp_call_tool("NetworkControlApp_set_gain",
                                   {"node_id": 8, "target_gain": 15})
"""

from .client import AicApiClient, AppInfo, MCPTool, create_client

__version__ = "1.1.0"
__all__ = ['AicApiClient', 'AppInfo', 'MCPTool', 'create_client']
