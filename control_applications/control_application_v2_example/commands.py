# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Command Definitions.

This module defines all commands specific to the network control application.
Commands are registered with the ai_nn_controller framework via an explicit registration call.

To add a new command:
1. Define a handler function that takes (node_id, value) and returns JSON
2. Define the JSON schema for the command parameters
3. Call register_command() with name, handler, and schema
"""

import json
from ai_nn_controller.registry import register_command  # Direct import from registry module


# =============================================================================
# Command Handlers
# =============================================================================

def set_gain_handler(node_id: int, value: dict) -> str:
    """
    Handle SET_GAIN command for amplifiers.

    Transforms generic parameters to node-specific payload:
    - line amp: {"target_gain": value}
    - preamp: {"preamp_gain": value}
    - booster: {"booster_gain": value}

    Args:
        node_id: Target node ID
        value: {"amp_type": "line|preamp|booster", "target_gain": float}

    Returns:
        JSON string payload
    """
    amp_type = value.get("amp_type", "line")
    gain = value.get("target_gain")

    if amp_type == "preamp":
        return json.dumps({"preamp_gain": gain})
    elif amp_type == "booster":
        return json.dumps({"booster_gain": gain})
    else:
        # Default line amp
        return json.dumps({"target_gain": gain})


def set_voa_handler(node_id: int, value: dict) -> str:
    """
    Handle SET_VOA command for Variable Optical Attenuators.

    Transforms generic parameters to node-specific payload:
    - mux direction: {"voa_mux": value, "channel": n}
    - demux direction: {"voa_demux": value, "channel": n}

    Args:
        node_id: Target node ID
        value: {"channel": int, "attenuation": float, "direction": "mux|demux"}

    Returns:
        JSON string payload
    """
    direction = value.get("direction", "mux")
    channel = value.get("channel")
    attenuation = value.get("attenuation")

    payload = {"channel": channel}

    if direction == "mux":
        payload["voa_mux"] = attenuation
    elif direction == "demux":
        payload["voa_demux"] = attenuation
    else:
        payload["voa_attenuation"] = attenuation

    return json.dumps(payload)


def set_tilt_handler(node_id: int, value: dict) -> str:
    """
    Handle SET_TILT command for spectral tilt compensation.

    Args:
        node_id: Target node ID
        value: {"tilt_value": float}

    Returns:
        JSON string payload
    """
    return json.dumps({"tilt_value": value.get("tilt_value")})


def launch_power_handler(node_id: int, value: dict) -> str:
    """
    Handle LAUNCH_POWER command for transmitter power adjustment.

    Args:
        node_id: Target node ID
        value: {"power_adjustment": float}

    Returns:
        JSON string payload
    """
    return json.dumps({"launch_power_adjustment": value.get("power_adjustment")})


def channel_allocation_handler(node_id: int, value: dict) -> str:
    """
    Handle CHANNEL_ALLOCATION command.

    Args:
        node_id: Target node ID
        value: {"allocation": dict}

    Returns:
        JSON string payload
    """
    return json.dumps({"channel_allocation": value.get("allocation")})


def amplifier_gain_handler(node_id: int, value: dict) -> str:
    """
    Handle AMPLIFIER_GAIN command.

    Args:
        node_id: Target node ID
        value: {"gain": float}

    Returns:
        JSON string payload
    """
    return json.dumps({"amplifier_gain": value.get("gain")})


# =============================================================================
# Command Schemas (for MCP tool generation)
# =============================================================================

SET_GAIN_SCHEMA = {
    "description": "Set the target gain for an amplifier (line amp, preamp, or booster)",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "amp_type": {
            "type": "string",
            "enum": ["line", "preamp", "booster"],
            "default": "line",
            "description": "Type of amplifier: 'line' for ILA nodes, 'preamp'/'booster' for ROADMs"
        },
        "target_gain": {
            "type": "number",
            "description": "Target gain value in dB"
        }
    },
    "required": ["node_id", "target_gain"]
}

SET_VOA_SCHEMA = {
    "description": "Set the Variable Optical Attenuator (VOA) attenuation for a specific channel",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "channel": {
            "type": "integer",
            "description": "Channel number to adjust"
        },
        "attenuation": {
            "type": "number",
            "description": "Attenuation value in dB"
        },
        "direction": {
            "type": "string",
            "enum": ["mux", "demux"],
            "default": "mux",
            "description": "VOA direction: 'mux' for multiplexer side, 'demux' for demultiplexer side"
        }
    },
    "required": ["node_id", "channel", "attenuation"]
}

SET_TILT_SCHEMA = {
    "description": "Set the spectral tilt compensation for an amplifier",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "tilt_value": {
            "type": "number",
            "description": "Tilt compensation value in dB"
        }
    },
    "required": ["node_id", "tilt_value"]
}

LAUNCH_POWER_SCHEMA = {
    "description": "Adjust the launch power for a transmitter",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "power_adjustment": {
            "type": "number",
            "description": "Power adjustment value in dBm"
        }
    },
    "required": ["node_id", "power_adjustment"]
}

CHANNEL_ALLOCATION_SCHEMA = {
    "description": "Set the channel allocation configuration",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "allocation": {
            "type": "object",
            "description": "Channel allocation configuration"
        }
    },
    "required": ["node_id", "allocation"]
}

AMPLIFIER_GAIN_SCHEMA = {
    "description": "Set amplifier gain command",
    "properties": {
        "node_id": {
            "type": "integer",
            "description": "The ID of the node to control"
        },
        "gain": {
            "type": "number",
            "description": "Gain value in dB"
        }
    },
    "required": ["node_id", "gain"]
}


# =============================================================================
# Register Commands with Framework
# =============================================================================

def register_specific_commands():
    """Register all specific commands with the framework."""

    register_command(
        name="SET_GAIN",
        handler=set_gain_handler,
        schema=SET_GAIN_SCHEMA
    )

    register_command(
        name="SET_VOA",
        handler=set_voa_handler,
        schema=SET_VOA_SCHEMA
    )

    register_command(
        name="SET_TILT",
        handler=set_tilt_handler,
        schema=SET_TILT_SCHEMA
    )

    register_command(
        name="LAUNCH_POWER",
        handler=launch_power_handler,
        schema=LAUNCH_POWER_SCHEMA
    )

    register_command(
        name="CHANNEL_ALLOCATION",
        handler=channel_allocation_handler,
        schema=CHANNEL_ALLOCATION_SCHEMA
    )

    register_command(
        name="AMPLIFIER_GAIN",
        handler=amplifier_gain_handler,
        schema=AMPLIFIER_GAIN_SCHEMA
    )

# Explicit capability metadata for plugin-style registration
COMMAND_CAPABILITIES = [
    "SET_GAIN",
    "SET_VOA",
    "SET_TILT",
    "LAUNCH_POWER",
    "CHANNEL_ALLOCATION",
    "AMPLIFIER_GAIN",
]


def get_command_capabilities() -> list[str]:
    """Return command capability names exposed by this application."""
    return list(COMMAND_CAPABILITIES)
