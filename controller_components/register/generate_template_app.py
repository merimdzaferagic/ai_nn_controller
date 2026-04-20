# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
Generate a template control application based on currently registered nodes.

Run this inside the aic_register container *after* nodes register so Redis
contains the latest PM/control capabilities.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import redis


DEFAULT_APP_NAME = "template_app"
DEFAULT_APP_ID = 100
DEFAULT_UPDATE_TIME = 2
DEFAULT_COMPOSE_OUTPUT = "/workspace/docker-compose-test.yml"

NODE_SERVICE_MAP = {
    3: ("amp1_node", "./network_nodes/dummy_nodes/amp1_node/", "Amp1"),
    4: ("roadm1_node", "./network_nodes/dummy_nodes/roadm1_node/", "ROADM1"),
    5: ("amp2_node", "./network_nodes/dummy_nodes/amp2_node/", "Amp2"),
    6: ("amp3_node", "./network_nodes/dummy_nodes/amp3_node/", "Amp3"),
    7: ("roadm2_node", "./network_nodes/dummy_nodes/roadm2_node/", "ROADM2"),
    8: ("roadm3_node", "./network_nodes/dummy_nodes/roadm3_with_command/", "ROADM3"),
}


def _sorted_ints(values) -> List[int]:
    return sorted(int(v) for v in values)


def _sorted_strs(values) -> List[str]:
    return sorted(str(v) for v in values)


def _collect_registry_state() -> Tuple[List[int], Dict[int, List[str]], Dict[int, List[str]]]:
    r = redis.Redis(host="redis", port=6379, decode_responses=True)

    node_ids = _sorted_ints(r.smembers("network_nodes:network_node_list"))
    read_measurements: Dict[int, List[str]] = {}
    control_functions: Dict[int, List[str]] = {}

    for node_id in node_ids:
        pm_key = f"network_nodes:network_node_pm_list:{node_id}"
        ctrl_key = f"network_nodes:network_node_ctrl_list:{node_id}"

        pms = _sorted_strs(r.smembers(pm_key))
        ctrls = _sorted_strs(r.smembers(ctrl_key))

        if pms:
            read_measurements[node_id] = pms
        if ctrls:
            control_functions[node_id] = ctrls

    return node_ids, read_measurements, control_functions


def _format_dict_of_lists(
    mapping: Dict[int, List[str]],
    base_indent: int = 4,
    indent_size: int = 4,
) -> str:
    if not mapping:
        return " " * base_indent + "{}"

    lines = [" " * base_indent + "{"]
    for node_id in sorted(mapping.keys()):
        lines.append(" " * (base_indent + indent_size) + f"{node_id}: [")
        for item in mapping[node_id]:
            lines.append(" " * (base_indent + indent_size * 2) + f"\"{item}\",")
        lines.append(" " * (base_indent + indent_size) + "],")
    lines.append(" " * base_indent + "}")
    return "\n".join(lines)


def _render_aic_app(
    app_name: str,
    app_id: int,
    update_time: int,
    read_measurements: Dict[int, List[str]],
    control_functions: Dict[int, List[str]],
) -> str:
    read_repr = _format_dict_of_lists(read_measurements)
    ctrl_repr = _format_dict_of_lists(control_functions)

    all_commands = []
    for cmds in control_functions.values():
        all_commands.extend(cmds)
    unique_commands = sorted(set(all_commands))
    validator_command = unique_commands[0] if unique_commands else "EXAMPLE_COMMAND"

    return f'''from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.decorators.command_validator import command_validator
from ai_nn_controller.decorators.agent_controlled import agent_controlled
from ai_nn_controller.AicApp import AicApp
from ai_nn_controller.AicController import AicController
from typing import Optional, Tuple
import argparse
import time

# Import commands module to register specific commands with the framework.
# Must happen before @aic_app executes so MCP schema generation can query
# the command registry at decoration time.
import commands


@aic_app(name="{app_name}")
class TemplateApp(AicApp):
    """
    Template control application generated from registered nodes.

    - read_measurements and control_functions reflect what the register knows.
    - Validators and agent_controlled handlers are optional stubs shown below.
    - Replace the process() body with your control logic.
    """
    aic_app_id = {app_id}
    control_loop_update_time = {update_time}

    read_measurements = {read_repr}

    control_functions = {ctrl_repr}

    # =========================================================================
    # OPTIONAL: Command Validator
    # Returning (True, None) allows the command through; (False, "reason") blocks it.
    # =========================================================================
    @classmethod
    @command_validator("{validator_command}")
    def validate_command_stub(cls, params: dict) -> Tuple[bool, Optional[str]]:
        """
        Optional validator stub. Replace with real validation logic if needed.
        """
        return True, None

    # =========================================================================
    # OPTIONAL: Agent-Controlled Operation
    # This handler executes inside the process loop with access to live
    # measurements. It is exposed as an MCP tool to AI agents.
    # =========================================================================
    @classmethod
    @agent_controlled(
        name="template_noop",
        description="Optional stub handler with access to live measurements",
        schema={{"properties": {{"note": {{"type": "string"}}}}, "required": []}},
    )
    def handle_agent_stub(cls, request, measurements):
        """
        Optional agent-controlled stub. Useful for testing MCP integration.
        """
        return {{
            "status": "ok",
            "note": request.get("note"),
            "node_count": len(measurements),
        }}

    @classmethod
    def process(cls, measurements):
        """
        Called periodically with the latest measurements from all subscribed nodes.

        measurements: Dict[int, List[Dict]] — node_id to list of measurement dicts
                      (oldest first; use measurements[node_id][-1] for the latest)
        """
        print(f"[{app_name}] Processing measurements at {{time.time():.2f}}")
        if not measurements:
            print(f"[{app_name}] No measurements received yet")
            return

        for node_id in sorted(measurements.keys()):
            node_data = measurements.get(node_id, [])
            latest = node_data[-1] if node_data else None
            if latest:
                print(f"[{app_name}] Node {{node_id}}: {{latest}}")

        # TODO: add control logic here, e.g.:
        # cls.add_command(("COMMAND_NAME", {{"node_id": 8, "value": {{...}}}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="{app_name} AIC Application")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output for debugging")
    parser.add_argument("--port", "-p", type=int, default=8000,
                        help="Port for the FastAPI server (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host address for the FastAPI server (default: 0.0.0.0)")
    args = parser.parse_args()

    AicController(
        with_api=True,
        api_host=args.host,
        api_port=args.port,
        verbose=args.verbose,
    ).run()
'''


def _render_commands(control_functions: Dict[int, List[str]]) -> str:
    all_commands = []
    for cmds in control_functions.values():
        all_commands.extend(cmds)
    unique_commands = sorted(set(all_commands))

    lines = [
        '"""',
        "Auto-generated command registry.",
        "",
        "Each command has a stub handler and a minimal JSON schema.",
        "Replace the handler bodies and schema properties with real definitions.",
        '"""',
        "",
        "import json",
        "from typing import List",
        "from ai_nn_controller.registry import register_command",
        "",
        "",
        "# =============================================================================",
        "# Command Handlers",
        "# =============================================================================",
        "",
    ]

    if not unique_commands:
        lines += [
            "# No control functions were registered at generation time.",
            "# Add handlers here as nodes with controls come online.",
            "",
        ]
    else:
        for cmd in unique_commands:
            fn_name = cmd.lower() + "_handler"
            lines += [
                f"def {fn_name}(node_id: int, value: dict) -> str:",
                f'    """',
                f"    Handle {cmd} command.",
                f"",
                f"    Args:",
                f"        node_id: Target node ID",
                f"        value: Command parameters dict",
                f"",
                f"    Returns:",
                f"        JSON string payload sent to the node",
                f'    """',
                f"    return json.dumps(value)",
                f"",
                f"",
            ]

    lines += [
        "# =============================================================================",
        "# Command Schemas (used for MCP tool generation)",
        "# =============================================================================",
        "",
    ]

    if unique_commands:
        for cmd in unique_commands:
            schema_var = cmd + "_SCHEMA"
            lines += [
                f"{schema_var} = {{",
                f'    "description": "Execute {cmd} command on a network node",',
                f'    "properties": {{',
                f'        "node_id": {{',
                f'            "type": "integer",',
                f'            "description": "Target node ID",',
                f'        }},',
                f'        "value": {{',
                f'            "type": "object",',
                f'            "description": "Command parameters (replace with specific fields)",',
                f'        }},',
                f'    }},',
                f'    "required": ["node_id", "value"],',
                f"}}",
                f"",
            ]

    lines += [
        "",
        "# =============================================================================",
        "# Registration",
        "# =============================================================================",
        "",
        "def register_specific_commands() -> None:",
        '    """Register all commands with the ai_nn_controller framework."""',
    ]

    if not unique_commands:
        lines.append("    pass  # No commands to register")
    else:
        for cmd in unique_commands:
            fn_name = cmd.lower() + "_handler"
            schema_var = cmd + "_SCHEMA"
            lines += [
                f"    register_command(",
                f'        name="{cmd}",',
                f"        handler={fn_name},",
                f"        schema={schema_var},",
                f"    )",
            ]

    lines += [
        "",
        "",
        "def get_command_capabilities() -> List[str]:",
        '    """Return command names exposed by this application."""',
        "    return [" + ", ".join(f'"{c}"' for c in unique_commands) + "]",
        "",
        "",
        "# Auto-register commands when this module is imported.",
        "# This ensures commands are registered before @aic_app decorators execute.",
        "register_specific_commands()",
        "",
    ]

    return "\n".join(lines)


def _render_pyproject_toml(app_name: str) -> str:
    # Convert folder name (e.g. "template_app") to package name ("template-app")
    package_name = app_name.replace("_", "-")
    entry_key = f"{app_name}:aic_app:commands"
    return f"""[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name}"
version = "0.1.0"
description = "Auto-generated template control application for ai_nn_controller"
requires-python = ">=3.9"
dependencies = ["ai_nn_controller>=1.0.0"]

[project.entry-points."ai_nn_controller.app_init"]
"{entry_key}" = "ai_nn_controller.plugins.entrypoints:bootstrap_application_bundle"

[tool.setuptools]
py-modules = ["aic_app", "commands"]
"""


def _render_dockerfile(app_name: str) -> str:
    return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y net-tools procps curl

# Copy the application package and install it (picks up pyproject.toml + dependencies)
COPY control_applications/{app_name}/ /app/
RUN pip install --no-cache-dir /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Run the AIC app directly - it starts the FastAPI server via with_api=True
CMD ["python3", "aic_app.py"]
"""


def _render_aic_app_conf() -> str:
    return """# register ip address
ip_address = aic_register

# port to register the app
register_port = 5558
"""


def _render_docker_compose(app_name: str, node_ids: List[int]) -> str:
    lines = [
        'version: "3.8"',
        "",
        "# Auto-generated docker-compose for registered nodes + template app",
        "",
        "services:",
        "  # Redis database for state",
        "  redis:",
        "    container_name: redis",
        "    image: redis:7-alpine",
        "    ports:",
        '      - "6379:6379"',
        "    networks:",
        "      - aic_network",
        "    healthcheck:",
        '      test: ["CMD", "redis-cli", "ping"]',
        "      interval: 5s",
        "      timeout: 3s",
        "      retries: 5",
        "",
        "  # Register service - handles node and app registration",
        "  aic_register:",
        "    container_name: aic_register",
        "    build:",
        "      context: ./controller_components/register/",
        "      dockerfile: Dockerfile",
        "    volumes:",
        "      - ./controller_components/register/:/register",
        "      - ./control_applications/:/control_applications",
        "      - ./:/workspace",
        "    tty: true",
        "    stdin_open: true",
        "    command: python3 register.py",
        "    depends_on:",
        "      redis:",
        "        condition: service_healthy",
        "    networks:",
        "      - aic_network",
        "    ports:",
        '      - "5558:5558"',
        "    environment:",
        "      - PYTHONUNBUFFERED=1",
        "",
        "  # Message broker",
        "  node_msg_broker:",
        "    container_name: node_msg_broker",
        "    build:",
        "      context: ./controller_components/node_msg_broker/",
        "      dockerfile: Dockerfile",
        "    volumes:",
        "      - ./controller_components/node_msg_broker/:/node_msg_broker",
        "    tty: true",
        "    stdin_open: true",
        "    depends_on:",
        "      - aic_register",
        "    networks:",
        "      - aic_network",
        "    ports:",
        '      - "5554:5554"',
        '      - "5555:5555"',
        '      - "5557:5557"',
        "    environment:",
        "      - PYTHONUNBUFFERED=1",
        "",
    ]

    for node_id in node_ids:
        if node_id not in NODE_SERVICE_MAP:
            continue
        service_name, context, label = NODE_SERVICE_MAP[node_id]
        lines.extend([
            f"  # {label} Node (cell_id = {node_id})",
            f"  {service_name}:",
            f"    container_name: {service_name}",
            "    build:",
            f"      context: {context}",
            "      dockerfile: Dockerfile",
            "    volumes:",
            f"      - {context}:/node",
            "    tty: true",
            "    stdin_open: true",
            "    depends_on:",
            "      - aic_register",
            "      - node_msg_broker",
            "    networks:",
            "      - aic_network",
            "    command: >",
            '      sh -c "sleep 5 && python3 node.py"',
            "    environment:",
            "      - PYTHONUNBUFFERED=1",
            "",
        ])

    lines.extend([
        "  # AIC Application Server with FastAPI",
        f"  # Installs ai_nn_controller and {app_name} as packages, then runs the app.",
        "  aic_server:",
        "    container_name: aic_server",
        "    build:",
        "      context: ./",
        f"      dockerfile: control_applications/{app_name}/Dockerfile",
        "    volumes:",
        f"      - ./control_applications/{app_name}/:/app",
        "      - ./controller_components/ai_nn_controller/:/ai_nn_controller",
        "    ports:",
        '      - "8000:8000"',
        "    networks:",
        "      - aic_network",
        "    environment:",
        "      - PYTHONUNBUFFERED=1",
        "    command: >",
        '      sh -c "sleep 25 && pip install --no-cache-dir /ai_nn_controller && pip install --no-cache-dir /app && python3 aic_app.py --verbose"',
        "",
        "networks:",
        "  aic_network:",
        "    driver: bridge",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a template control app from register state.")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME, help="App name (folder + decorator name).")
    parser.add_argument("--app-id", type=int, default=DEFAULT_APP_ID, help="aic_app_id value.")
    parser.add_argument("--update-time", type=int, default=DEFAULT_UPDATE_TIME, help="Control loop update time (seconds).")
    parser.add_argument("--output-root", default="/control_applications", help="Root output directory.")
    parser.add_argument(
        "--compose-output",
        default=DEFAULT_COMPOSE_OUTPUT,
        help="Path to write docker-compose-test.yml",
    )
    args = parser.parse_args()

    node_ids, read_measurements, control_functions = _collect_registry_state()
    if not node_ids:
        print("No registered nodes found in Redis. Run this after nodes register.")
        return 1
    unknown_nodes = [node_id for node_id in node_ids if node_id not in NODE_SERVICE_MAP]
    if unknown_nodes:
        print(f"Warning: No service mapping for node IDs: {unknown_nodes}. They will be skipped in compose.")

    output_root = Path(args.output_root)
    app_dir = output_root / args.app_name
    app_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "aic_app.py").write_text(
        _render_aic_app(args.app_name, args.app_id, args.update_time, read_measurements, control_functions),
        encoding="utf-8",
    )
    (app_dir / "commands.py").write_text(
        _render_commands(control_functions),
        encoding="utf-8",
    )
    (app_dir / "pyproject.toml").write_text(
        _render_pyproject_toml(args.app_name),
        encoding="utf-8",
    )
    (app_dir / "Dockerfile").write_text(
        _render_dockerfile(args.app_name),
        encoding="utf-8",
    )
    (app_dir / "aic_app.conf").write_text(
        _render_aic_app_conf(),
        encoding="utf-8",
    )

    compose_path = Path(args.compose_output)
    compose_path.write_text(
        _render_docker_compose(args.app_name, node_ids),
        encoding="utf-8",
    )

    print(f"Template app generated at: {app_dir}")
    print(f"  aic_app.py     — app class with process(), validator, and agent stub")
    print(f"  commands.py    — command handlers, schemas, and register_specific_commands()")
    print(f"  pyproject.toml — package metadata and ai_nn_controller.app_init entry point")
    print(f"  Dockerfile     — installs app as a package via pip install /app")
    print(f"  aic_app.conf   — register address")
    print(f"Docker compose generated at: {compose_path}")
    print("Stop the original stack then run the test stack:")
    print(f"  docker compose down")
    print(f"  docker-compose -f {compose_path} up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
