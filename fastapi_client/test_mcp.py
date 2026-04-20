# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
Test script for MCP functionality in the AIC API Client.

This script demonstrates how to use the MCP features of the client
to discover and execute tools for network control.

Usage:
    python test_mcp.py [--url http://aic_server:8000]
"""

import sys
import argparse
from client import AicApiClient, create_client


def test_mcp_discovery(client: AicApiClient):
    """Test MCP tool discovery features."""
    print("\n" + "="*70)
    print("  MCP Tool Discovery Tests")
    print("="*70)

    # Test 1: Get MCP server info
    print("\n[Test 1] Getting MCP server info...")
    try:
        info = client.mcp_get_info()
        print(f"  Server: {info.get('name')} v{info.get('version')}")
        print(f"  Stats: {info.get('stats')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: List all tools
    print("\n[Test 2] Listing all MCP tools...")
    try:
        tools = client.mcp_list_tools()
        print(f"  Found {len(tools)} tools:")
        for tool in tools:
            print(f"    - {tool.name}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 3: Get tool schema
    if tools:
        print(f"\n[Test 3] Getting schema for first tool: {tools[0].name}")
        try:
            schema = client.mcp_get_tool_schema(tools[0].name)
            print(f"  Description: {schema.get('description')}")
            print(f"  App: {schema.get('app')}")
            print(f"  Type: {schema.get('type')}")
            print(f"  Schema: {schema.get('inputSchema')}")
        except Exception as e:
            print(f"  Error: {e}")

    # Test 4: Print tools in formatted way
    print("\n[Test 4] Formatted tool listing...")
    try:
        client.mcp_print_tools()
    except Exception as e:
        print(f"  Error: {e}")

    return tools


def test_mcp_validation(client: AicApiClient, tools):
    """Test MCP tool validation features."""
    print("\n" + "="*70)
    print("  MCP Tool Validation Tests")
    print("="*70)

    if not tools:
        print("  No tools available for validation testing")
        return

    # Find a set_gain tool for testing
    gain_tool = None
    for tool in tools:
        if 'set_gain' in tool.name:
            gain_tool = tool
            break

    if not gain_tool:
        print("  No set_gain tool found for validation testing")
        return

    # Test 1: Valid arguments
    print(f"\n[Test 1] Validating valid arguments for {gain_tool.name}...")
    valid_args = {"node_id": 8, "target_gain": 15.0}
    errors = client.mcp_validate_tool_call(gain_tool.name, valid_args)
    if errors:
        print(f"  Unexpected errors: {errors}")
    else:
        print(f"  Valid: {valid_args}")

    # Test 2: Missing required parameter
    print(f"\n[Test 2] Validating missing required parameter...")
    invalid_args = {"target_gain": 15.0}  # Missing node_id
    errors = client.mcp_validate_tool_call(gain_tool.name, invalid_args)
    if errors:
        print(f"  Expected errors: {errors}")
    else:
        print(f"  Unexpected: No errors for missing parameter")

    # Test 3: Invalid enum value
    print(f"\n[Test 3] Validating invalid enum value...")
    invalid_args = {"node_id": 8, "target_gain": 15.0, "amp_type": "invalid"}
    errors = client.mcp_validate_tool_call(gain_tool.name, invalid_args)
    if errors:
        print(f"  Expected errors: {errors}")
    else:
        print(f"  Unexpected: No errors for invalid enum")


def test_mcp_execution(client: AicApiClient, app_name: str = "NetworkControlApp"):
    """Test MCP tool execution features."""
    print("\n" + "="*70)
    print("  MCP Tool Execution Tests")
    print("="*70)

    # Test 1: Get app state via MCP
    print(f"\n[Test 1] Getting state for {app_name} via MCP...")
    try:
        result = client.mcp_get_state(app_name)
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Get measurements via MCP
    print(f"\n[Test 2] Getting measurements for {app_name} via MCP...")
    try:
        result = client.mcp_get_measurements(app_name)
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 3: Start app via MCP
    print(f"\n[Test 3] Starting {app_name} via MCP...")
    try:
        result = client.mcp_start_app(app_name)
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 4: Call tool directly
    print(f"\n[Test 4] Calling {app_name}_get_state directly...")
    try:
        result = client.mcp_call_tool(f"{app_name}_get_state", {})
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 5: Send MCP message
    print(f"\n[Test 5] Sending raw MCP message (tools/list)...")
    try:
        result = client.mcp_send_message("tools/list", {}, request_id=1)
        print(f"  Response ID: {result.get('id')}")
        print(f"  Tools count: {len(result.get('result', {}).get('tools', []))}")
    except Exception as e:
        print(f"  Error: {e}")


def test_mcp_convenience(client: AicApiClient, app_name: str = "NetworkControlApp"):
    """Test MCP convenience methods."""
    print("\n" + "="*70)
    print("  MCP Convenience Method Tests")
    print("="*70)

    # These tests only print what would happen - actual execution depends on server

    print(f"\n[Info] The following convenience methods are available:")
    print(f"  - client.mcp_set_gain('{app_name}', node_id=8, target_gain=15.0)")
    print(f"  - client.mcp_set_voa('{app_name}', node_id=8, channel=1, attenuation=5.0)")
    print(f"  - client.mcp_set_tilt('{app_name}', node_id=8, tilt_value=1.0)")
    print(f"  - client.mcp_get_measurements('{app_name}', node_id=8)")
    print(f"  - client.mcp_get_state('{app_name}')")
    print(f"  - client.mcp_set_state('{app_name}', 'running')")
    print(f"  - client.mcp_start_app('{app_name}')")
    print(f"  - client.mcp_stop_app('{app_name}')")
    print(f"  - client.mcp_pause_app('{app_name}')")


def main():
    parser = argparse.ArgumentParser(description="Test MCP functionality")
    parser.add_argument("--url", default="http://aic_server:8000",
                        help="Base URL of the AIC API server")
    parser.add_argument("--app", default="NetworkControlApp",
                        help="App name to test with")
    parser.add_argument("--skip-execution", action="store_true",
                        help="Skip execution tests (discovery only)")
    args = parser.parse_args()

    print(f"\nConnecting to AIC API at {args.url}...")

    with AicApiClient(args.url) as client:
        # Test health first
        try:
            health = client.health_check()
            print(f"Server healthy: {health.get('status')}")
            print(f"Apps: {health.get('registered_apps')}")
        except Exception as e:
            print(f"Cannot connect to server: {e}")
            print("Make sure the AIC FastAPI server is running.")
            sys.exit(1)

        # Run tests
        tools = test_mcp_discovery(client)
        test_mcp_validation(client, tools)

        if not args.skip_execution:
            test_mcp_execution(client, args.app)

        test_mcp_convenience(client, args.app)

    print("\n" + "="*70)
    print("  All MCP tests completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
