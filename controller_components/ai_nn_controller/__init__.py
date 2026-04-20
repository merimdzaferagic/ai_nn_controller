# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
ai_nn_controller Framework
"""

from .AicApp import AicApp
from .AicController import AicController
from .config import AicConfig, vprint
from .decorators.agent_controlled import agent_controlled
from .decorators.aic_app import aic_app
from .decorators.command_validator import command_validator
from .managers.AicManager import AicManager
from .plugins import CapabilityMetadata, PluginRegistry
from .registry import (
    clear_registry,
    execute_command,
    get_all_schemas,
    get_command_description,
    get_command_handler,
    get_command_schema,
    get_measurement_schema,
    get_state_schema,
    has_command,
    list_commands,
    register_command,
    register_commands,
)

__all__ = [
    "AicApp",
    "AicController",
    "AicManager",
    "AicConfig",
    "vprint",
    "aic_app",
    "command_validator",
    "agent_controlled",
    "register_command",
    "register_commands",
    "get_command_handler",
    "get_command_schema",
    "get_command_description",
    "list_commands",
    "has_command",
    "execute_command",
    "get_all_schemas",
    "clear_registry",
    "get_measurement_schema",
    "get_state_schema",
    "PluginRegistry",
    "CapabilityMetadata",
]

__version__ = "1.0.0"
