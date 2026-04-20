# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
Interactive CLI for AIC API Client

This provides an interactive command-line interface for managing
AIC applications via the FastAPI server.
"""

import sys
import cmd
import json
from client import AicApiClient


class AicCli(cmd.Cmd):
    """Interactive CLI for AIC API operations."""

    intro = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║           AIC Application Controller - Interactive CLI            ║
    ╚═══════════════════════════════════════════════════════════════════╝

    Type 'help' or '?' to list commands.
    Type 'help <command>' for detailed help on a specific command.
    """

    prompt = 'aic> '

    def __init__(self, base_url="http://aic_server:8000"):
        super().__init__()
        self.client = AicApiClient(base_url)
        self.base_url = base_url
        print(f"\n    Connected to: {base_url}\n")

    # ==================== Health & Info ====================

    def do_health(self, arg):
        """Check API health status: health"""
        try:
            health = self.client.health_check()
            print(f"\n  Status: {health.get('status')}")
            print(f"  Controller Initialized: {health.get('controller_initialized')}")
            print(f"  Registered Apps: {health.get('registered_apps')}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_info(self, arg):
        """Get API information: info"""
        try:
            info = self.client.get_api_info()
            print(f"\n  API: {info.get('message')}")
            print(f"  Version: {info.get('version')}")
            print(f"\n  Available Endpoints:")
            for name, path in info.get('endpoints', {}).items():
                print(f"    - {name}: {path}")
            print()
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    # ==================== App Management ====================

    def do_list(self, arg):
        """List all registered apps: list"""
        try:
            apps = self.client.list_apps()
            print(f"\n  Registered Applications ({len(apps)}):")
            print(f"  {'-'*66}")
            for app in apps:
                print(f"  {app.name:<25} state={app.state:<10} nodes={app.cell_ids}")
            print()
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_appinfo(self, arg):
        """Get detailed app information: appinfo <app_name>"""
        if not arg:
            print("\n✗ Usage: appinfo <app_name>\n")
            return

        try:
            info = self.client.get_app_info(arg)
            print(f"\n  App: {info.get('app_name')}")
            print(f"  Node ID: {info.get('node_id')}")
            print(f"  Cell IDs: {info.get('cell_ids')}")
            print(f"  Time Interval: {info.get('time_interval')}s")

            print(f"\n  Measurements:")
            for node_id, measurements in info.get('read_measurements', {}).items():
                print(f"    Node {node_id}: {measurements}")

            print(f"\n  Control Functions:")
            for node_id, functions in info.get('control_functions', {}).items():
                print(f"    Node {node_id}: {functions}")
            print()
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_state(self, arg):
        """Get app state: state <app_name>"""
        if not arg:
            print("\n✗ Usage: state <app_name>\n")
            return

        try:
            state = self.client.get_app_state(arg)
            print(f"\n  {arg}: {state}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_start(self, arg):
        """Start an app: start <app_name>"""
        if not arg:
            print("\n✗ Usage: start <app_name>\n")
            return

        try:
            result = self.client.start_app(arg)
            print(f"\n  ✓ {result['app']}: {result['previous_state']} -> {result['state']}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_stop(self, arg):
        """Stop an app: stop <app_name>"""
        if not arg:
            print("\n✗ Usage: stop <app_name>\n")
            return

        try:
            result = self.client.stop_app(arg)
            print(f"\n  ✓ {result['app']}: {result['previous_state']} -> {result['state']}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_pause(self, arg):
        """Pause an app: pause <app_name>"""
        if not arg:
            print("\n✗ Usage: pause <app_name>\n")
            return

        try:
            result = self.client.pause_app(arg)
            print(f"\n  ✓ {result['app']}: {result['previous_state']} -> {result['state']}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_resume(self, arg):
        """Resume a paused app: resume <app_name>"""
        if not arg:
            print("\n✗ Usage: resume <app_name>\n")
            return

        try:
            result = self.client.resume_app(arg)
            print(f"\n  ✓ {result['app']}: {result['previous_state']} -> {result['state']}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    # ==================== Measurements ====================

    def do_measurements(self, arg):
        """Get app measurements: measurements <app_name>"""
        if not arg:
            print("\n✗ Usage: measurements <app_name>\n")
            return

        try:
            measurements = self.client.get_measurements(arg)
            print(f"\n  Measurements for {arg}:")
            if measurements:
                for node_id, data in measurements.items():
                    print(f"\n  Node {node_id}:")
                    if data:
                        for key, value in data.items():
                            print(f"    {key}: {value}")
                    else:
                        print(f"    No data yet")
            else:
                print(f"    No measurements available")
            print()
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_node(self, arg):
        """Get measurement for specific node: node <app_name> <node_id>"""
        args = arg.split()
        if len(args) != 2:
            print("\n✗ Usage: node <app_name> <node_id>\n")
            return

        app_name, node_id = args[0], int(args[1])

        try:
            data = self.client.get_node_measurement(app_name, node_id)
            print(f"\n  Node {node_id} (from {app_name}):")
            if data:
                for key, value in data.items():
                    print(f"    {key}: {value}")
            else:
                print(f"    No data available")
            print()
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    # ==================== Control Commands ====================

    def do_control(self, arg):
        """
        Send control command: control <app_name> <node_id> <command> <payload_json>

        Example:
            control NetworkControlApp 8 SET_GAIN '{"amp_type":"preamp","target_gain":12}'
        """
        args = arg.split(maxsplit=3)
        if len(args) != 4:
            print("\n✗ Usage: control <app_name> <node_id> <command> <payload_json>")
            print("  Example: control NetworkControlApp 8 SET_GAIN '{\"amp_type\":\"preamp\",\"target_gain\":12}'\n")
            return

        app_name, node_id, command, payload_str = args
        node_id = int(node_id)

        try:
            payload = json.loads(payload_str)
            result = self.client.send_control(app_name, node_id, command, payload)
            print(f"\n  ✓ Command sent:")
            print(f"    App: {result.get('app')}")
            print(f"    Node: {result.get('node_id')}")
            print(f"    Command: {result.get('command')}")
            print(f"    Status: {result.get('status')}\n")
        except json.JSONDecodeError:
            print(f"\n✗ Invalid JSON payload: {payload_str}\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    # ==================== Utility ====================

    def do_status(self, arg):
        """Print detailed status for an app: status <app_name>"""
        if not arg:
            print("\n✗ Usage: status <app_name>\n")
            return

        try:
            self.client.print_app_status(arg)
        except Exception as e:
            print(f"\n✗ Error: {e}\n")

    def do_exit(self, arg):
        """Exit the CLI: exit"""
        print("\nGoodbye!\n")
        return True

    def do_quit(self, arg):
        """Exit the CLI: quit"""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Exit on Ctrl+D"""
        print("\n")
        return self.do_exit(arg)


def main():
    """Main function to start the CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="AIC API Interactive CLI")
    parser.add_argument(
        '--url',
        default='http://aic_server:8000',
        help='Base URL of the FastAPI server (default: http://aic_server:8000)'
    )

    args = parser.parse_args()

    try:
        cli = AicCli(base_url=args.url)
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
