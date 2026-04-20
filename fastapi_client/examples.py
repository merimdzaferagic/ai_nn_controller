# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
Example usage of the AIC API Client

This script demonstrates all major functions of the FastAPI client.
"""

import sys
import time
from client import AicApiClient


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def example_basic_operations(client):
    """Demonstrate basic API operations."""
    print_section("Basic Operations")

    # Health check
    print("\n1. Health Check:")
    health = client.health_check()
    print(f"   Status: {health.get('status')}")
    print(f"   Controller initialized: {health.get('controller_initialized')}")

    # List apps
    print("\n2. List All Apps:")
    apps = client.list_apps()
    for app in apps:
        print(f"   - {app.name} (state: {app.state}, nodes: {app.cell_ids})")

    return apps


def example_app_lifecycle(client, app_name):
    """Demonstrate app lifecycle management."""
    print_section(f"App Lifecycle: {app_name}")

    # Get initial state
    print(f"\n1. Current state:")
    state = client.get_app_state(app_name)
    print(f"   {app_name} is {state}")

    # Start app
    print(f"\n2. Starting app...")
    result = client.start_app(app_name)
    print(f"   {result['app']} -> {result['state']}")
    time.sleep(2)

    # Verify running
    state = client.get_app_state(app_name)
    print(f"   Verified: {state}")

    # Pause app
    print(f"\n3. Pausing app...")
    result = client.pause_app(app_name)
    print(f"   {result['app']} -> {result['state']}")
    time.sleep(1)

    # Resume app
    print(f"\n4. Resuming app...")
    result = client.resume_app(app_name)
    print(f"   {result['app']} -> {result['state']}")
    time.sleep(2)

    # Stop app
    print(f"\n5. Stopping app...")
    result = client.stop_app(app_name)
    print(f"   {result['app']} -> {result['state']}")


def example_measurements(client, app_name):
    """Demonstrate measurement fetching."""
    print_section(f"Measurements: {app_name}")

    # Ensure app is running
    print(f"\n1. Ensuring {app_name} is running...")
    client.start_app(app_name)
    time.sleep(3)  # Wait for measurements to accumulate

    # Get all measurements
    print(f"\n2. Fetching measurements...")
    measurements = client.get_measurements(app_name)

    if measurements:
        print(f"   Received data from {len(measurements)} nodes:")
        for node_id, data in measurements.items():
            print(f"\n   Node {node_id}:")
            if data:
                for key, value in data.items():
                    print(f"     {key}: {value}")
            else:
                print(f"     No data yet")
    else:
        print("   No measurements available yet")

    # Get specific node measurement
    print(f"\n3. Fetching specific node measurement (node 3)...")
    node_data = client.get_node_measurement(app_name, 3)
    if node_data:
        print(f"   Node 3 data: {node_data}")
    else:
        print(f"   No data for node 3")


def example_control_commands(client, app_name):
    """Demonstrate sending control commands."""
    print_section(f"Control Commands: {app_name}")

    # Ensure app is running
    print(f"\n1. Ensuring {app_name} is running...")
    client.start_app(app_name)
    time.sleep(2)

    # Send control command
    print(f"\n2. Sending SET_GAIN command to node 8...")
    try:
        result = client.send_control(
            app_name=app_name,
            node_id=8,
            command="SET_GAIN",
            payload={
                "amp_type": "preamp",
                "target_gain": 11
            }
        )
        print(f"   Command sent successfully:")
        print(f"     App: {result.get('app')}")
        print(f"     Node: {result.get('node_id')}")
        print(f"     Status: {result.get('status')}")
    except Exception as e:
        print(f"   Error sending command: {e}")


def example_app_info(client, app_name):
    """Demonstrate getting detailed app information."""
    print_section(f"App Information: {app_name}")

    info = client.get_app_info(app_name)
    print(f"\n   App Name: {info.get('app_name')}")
    print(f"   Node ID: {info.get('node_id')}")
    print(f"   Cell IDs: {info.get('cell_ids')}")
    print(f"   Time Interval: {info.get('time_interval')}s")

    print(f"\n   Read Measurements:")
    for node_id, measurements in info.get('read_measurements', {}).items():
        print(f"     Node {node_id}: {measurements}")

    print(f"\n   Control Functions:")
    for node_id, functions in info.get('control_functions', {}).items():
        print(f"     Node {node_id}: {functions}")


def example_convenience_methods(client, app_name):
    """Demonstrate convenience methods."""
    print_section("Convenience Methods")

    # Start and wait
    print(f"\n1. Start {app_name} and wait for running state...")
    success = client.start_app_and_wait(app_name, timeout=10)
    if success:
        print(f"   ✓ {app_name} is running")
    else:
        print(f"   ✗ Failed to start {app_name}")

    # Print status
    print(f"\n2. Print app status:")
    client.print_app_status(app_name)


def main():
    """Main function to run all examples."""
    # Configuration
    BASE_URL = "http://aic_server:8000"  # Use service name in Docker

    print("="*70)
    print("  AIC API Client - Example Usage")
    print("="*70)
    print(f"\nConnecting to: {BASE_URL}")

    try:
        # Create client
        with AicApiClient(base_url=BASE_URL) as client:

            # Run examples
            apps = example_basic_operations(client)

            if not apps:
                print("\n✗ No apps registered. Make sure the server is running.")
                return

            # Use first app for demonstrations
            app_name = apps[0].name
            print(f"\nUsing '{app_name}' for demonstrations...")

            # App information
            example_app_info(client, app_name)

            # Lifecycle management
            example_app_lifecycle(client, app_name)

            # Measurements
            example_measurements(client, app_name)

            # Control commands
            example_control_commands(client, app_name)

            # Convenience methods
            example_convenience_methods(client, app_name)

            print_section("Examples Complete")
            print("\n✓ All examples executed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
