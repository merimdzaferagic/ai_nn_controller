# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
MCP (Model Context Protocol) integration for the AIC framework.

This module provides automatic MCP tool generation from @aic_app decorated classes,
allowing AI agents to control network nodes through a standardized interface.
"""

from .tool_registry import MCPToolRegistry
from .tool_generator import MCPToolGenerator
from ..registry import get_all_schemas

# For backward compatibility - get schemas from the registry
def get_command_schemas():
    """Get all registered command schemas. Use this instead of COMMAND_SCHEMAS constant."""
    return get_all_schemas()

__all__ = ["MCPToolRegistry", "MCPToolGenerator", "get_command_schemas"]
