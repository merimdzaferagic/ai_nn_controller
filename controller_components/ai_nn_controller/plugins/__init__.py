# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Plugin boundaries and discovery metadata for apps/nodes/commands."""

from .metadata import CapabilityMetadata, CompatibilityRange
from .registry import PluginRegistry
from .entrypoints import load_app_entrypoints

__all__ = ["CapabilityMetadata", "CompatibilityRange", "PluginRegistry", "load_app_entrypoints"]
