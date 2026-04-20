# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Command and Schema Registry for ai_nn_controller.

This module provides a registration API that allows applications to define
their own commands, handlers, and schemas. The framework uses this registry
to auto-generate MCP tools and process commands at runtime.

Usage:
    from ai_nn_controller import register_command

    def my_handler(node_id, value):
        return json.dumps({"param": value.get("param")})

    register_command(
        name="MY_COMMAND",
        handler=my_handler,
        schema={
            "description": "My custom command",
            "properties": {
                "node_id": {"type": "integer"},
                "param": {"type": "number"}
            },
            "required": ["node_id", "param"]
        }
    )
"""

from typing import Dict, Any, Callable, List, Optional
import json
from .config import vprint


# Internal registries
_command_handlers: Dict[str, Callable] = {}
_command_schemas: Dict[str, Dict[str, Any]] = {}
_measurement_schemas: Dict[str, Dict[str, Any]] = {}


def _generate_default_schema(name: str) -> Dict[str, Any]:
    """
    Generate a default schema for a command based on its name.

    Args:
        name: Command name (e.g., "SET_GAIN")

    Returns:
        A basic JSON Schema with node_id and payload properties
    """
    # Convert command name to readable description
    # SET_GAIN -> "Set gain", MY_COMMAND -> "My command"
    description = name.replace("_", " ").title()

    return {
        "description": f"Execute {description} command",
        "properties": {
            "node_id": {
                "type": "integer",
                "description": "The ID of the target node"
            },
            "payload": {
                "type": "object",
                "description": "Command parameters"
            }
        },
        "required": ["node_id"]
    }


def register_command(
    name: str,
    handler: Callable[[int, Dict[str, Any]], str],
    schema: Optional[Dict[str, Any]] = None
) -> None:
    """
    Register a command with its handler and optional schema.

    Args:
        name: Unique command name (e.g., "SET_GAIN", "SET_VOA")
        handler: Function that takes (node_id, value) and returns JSON string
        schema: Optional JSON Schema dict describing the command's parameters.
                If not provided, a default schema is auto-generated.

    Example (with schema):
        register_command(
            name="SET_GAIN",
            handler=lambda node_id, value: json.dumps({"gain": value["target_gain"]}),
            schema={
                "description": "Set amplifier gain",
                "properties": {
                    "node_id": {"type": "integer"},
                    "target_gain": {"type": "number"}
                },
                "required": ["node_id", "target_gain"]
            }
        )

    Example (without schema - uses default):
        register_command(
            name="MY_COMMAND",
            handler=my_handler
        )
    """
    if name in _command_handlers:
        vprint(f"[Registry] Warning: Overwriting existing command '{name}'")

    _command_handlers[name] = handler

    # Use provided schema or generate a default one
    if schema is None:
        schema = _generate_default_schema(name)
        vprint(f"[Registry] Registered command: {name} (using default schema)")
    else:
        _command_schemas[name] = schema
        vprint(f"[Registry] Registered command: {name}")

    _command_schemas[name] = schema


def register_commands(commands: Dict[str, Dict[str, Any]]) -> None:
    """
    Register multiple commands at once.

    Args:
        commands: Dict mapping command names to {"handler": fn, "schema": dict (optional)}

    Example:
        register_commands({
            "SET_GAIN": {
                "handler": set_gain_handler,
                "schema": {...}  # Optional - will use default if not provided
            },
            "SET_VOA": {
                "handler": set_voa_handler
                # No schema - will auto-generate default
            }
        })
    """
    for name, config in commands.items():
        register_command(
            name=name,
            handler=config["handler"],
            schema=config.get("schema")  # Use .get() to allow missing schema
        )


def get_command_handler(name: str) -> Optional[Callable]:
    """
    Get the handler function for a command.

    Args:
        name: Command name

    Returns:
        Handler function or None if not found
    """
    return _command_handlers.get(name)


def get_command_schema(name: str, allowed_node_ids: List[int] = None) -> Dict[str, Any]:
    """
    Get the JSON schema for a command, optionally constraining node_ids.

    Args:
        name: Command name
        allowed_node_ids: Optional list of allowed node IDs

    Returns:
        JSON Schema dict for the command's input parameters
    """
    if name not in _command_schemas:
        # Return a generic fallback schema
        return {
            "type": "object",
            "properties": {
                "node_id": {"type": "integer"},
                "payload": {"type": "object"}
            },
            "required": ["node_id"]
        }

    schema = _command_schemas[name]

    result = {
        "type": "object",
        "properties": dict(schema.get("properties", {})),
        "required": list(schema.get("required", []))
    }

    # Constrain node_id to allowed values if specified
    if allowed_node_ids and "node_id" in result["properties"]:
        result["properties"]["node_id"] = {
            "type": "integer",
            "enum": allowed_node_ids,
            "description": f"Node ID (allowed: {allowed_node_ids})"
        }

    return result


def get_command_description(name: str) -> str:
    """
    Get the description for a command.

    Args:
        name: Command name

    Returns:
        Description string or default message
    """
    schema = _command_schemas.get(name, {})
    return schema.get("description", f"Execute {name} command")


def list_commands() -> List[str]:
    """
    List all registered command names.

    Returns:
        List of command names
    """
    return list(_command_handlers.keys())


def has_command(name: str) -> bool:
    """
    Check if a command is registered.

    Args:
        name: Command name

    Returns:
        True if command exists
    """
    return name in _command_handlers


def execute_command(name: str, node_id: int, value: Dict[str, Any]) -> str:
    """
    Execute a command and return the JSON payload.

    Args:
        name: Command name
        node_id: Target node ID
        value: Command parameters

    Returns:
        JSON string payload for the command

    Raises:
        ValueError: If command is not registered
    """
    handler = _command_handlers.get(name)
    if handler is None:
        raise ValueError(f"Command '{name}' is not registered")

    return handler(node_id, value)


def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered command schemas.

    Returns:
        Dict mapping command names to schemas
    """
    return dict(_command_schemas)


def clear_registry() -> None:
    """
    Clear all registered commands. Useful for testing.
    """
    _command_handlers.clear()
    _command_schemas.clear()
    vprint("[Registry] Cleared all commands")


# Helper schemas for common patterns
def get_measurement_schema(node_ids: List[int], measurements_by_node: Dict[int, List[str]]) -> Dict[str, Any]:
    """
    Generate a JSON schema for the get_measurements tool.

    Args:
        node_ids: List of node IDs that can be queried
        measurements_by_node: Dict mapping node_id to list of measurement names

    Returns:
        JSON Schema dict for the measurements query
    """
    return {
        "type": "object",
        "properties": {
            "node_id": {
                "type": "integer",
                "enum": node_ids,
                "description": f"Optional: filter measurements to a specific node (available: {node_ids})"
            }
        },
        "required": []
    }


def get_state_schema() -> Dict[str, Any]:
    """
    Generate a JSON schema for the app state management tool.

    Returns:
        JSON Schema dict for state transitions
    """
    return {
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "enum": ["running", "paused", "stopped"],
                "description": "Target state for the application"
            }
        },
        "required": ["state"]
    }
