# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
MCP HTTP Proxy for stdio transport.

This script bridges stdio-based MCP clients (like Claude Desktop/Claude Code)
to the HTTP-based MCP server running in Docker.

Usage:
    python mcp_http_proxy.py [--url http://localhost:8000/mcp]
"""

import sys
import json
import argparse
import urllib.request
import urllib.error


def send_request(url: str, method: str, params: dict = None) -> dict:
    """Send a JSON-RPC request to the MCP HTTP server."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }
    if params:
        request_data["params"] = params

    data = json.dumps(request_data).encode('utf-8')
    req = urllib.request.Request(
        f"{url}/message",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": {"code": -32000, "message": str(e)}}
    except Exception as e:
        return {"error": {"code": -32000, "message": str(e)}}


def call_tool(url: str, name: str, arguments: dict) -> dict:
    """Call an MCP tool via HTTP."""
    data = json.dumps({"name": name, "arguments": arguments}).encode('utf-8')
    req = urllib.request.Request(
        f"{url}/tools/call",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def list_tools(url: str) -> list:
    """Get list of available tools."""
    req = urllib.request.Request(f"{url}/tools")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("tools", [])
    except Exception as e:
        sys.stderr.write(f"Error listing tools: {e}\n")
        return []


def handle_request(url: str, request: dict) -> dict:
    """Handle an incoming MCP request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "aic-controller-proxy",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "initialized":
        # No response needed for notification
        return None

    elif method == "tools/list":
        tools = list_tools(url)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools}
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = call_tool(url, tool_name, arguments)

        if "error" in result:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": True
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    parser = argparse.ArgumentParser(description="MCP HTTP Proxy")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/mcp",
        help="MCP HTTP server URL"
    )
    args = parser.parse_args()

    # Disable buffering for stdin/stdout
    sys.stdout = sys.stdout.detach()
    sys.stdin = sys.stdin.detach()

    while True:
        try:
            # Read a line from stdin
            line = sys.stdin.readline()
            if not line:
                break

            line = line.decode('utf-8').strip()
            if not line:
                continue

            # Parse JSON-RPC request
            request = json.loads(line)

            # Handle the request
            response = handle_request(args.url, request)

            # Send response (if any)
            if response:
                response_str = json.dumps(response) + "\n"
                sys.stdout.write(response_str.encode('utf-8'))
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            sys.stderr.write(f"JSON decode error: {e}\n".encode('utf-8') if isinstance(sys.stderr, type(sys.stdout)) else f"JSON decode error: {e}\n")
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n".encode('utf-8') if isinstance(sys.stderr, type(sys.stdout)) else f"Error: {e}\n")


if __name__ == "__main__":
    main()
