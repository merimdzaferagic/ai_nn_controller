# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Plugin framework — base classes, registry, and entry-point discovery."""

from .AicPlugin import AicPlugin, StoragePlugin, ModelRegistryPlugin, MonitoringPlugin
from .plugin_manager import PluginManager
from .decorators import aic_plugin
from .entrypoints import load_plugin_entrypoints, bootstrap_plugin_bundle
from .validator import validate_app_plugins

__all__ = [
    "AicPlugin",
    "StoragePlugin",
    "ModelRegistryPlugin",
    "MonitoringPlugin",
    "PluginManager",
    "aic_plugin",
    "load_plugin_entrypoints",
    "bootstrap_plugin_bundle",
    "validate_app_plugins",
]
