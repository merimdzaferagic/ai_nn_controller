# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
@aic_plugin decorator — registers an AicPlugin subclass with PluginManager.

Usage:
    from ai_nn_controller.plugin_framework import aic_plugin, AicPlugin

    @aic_plugin(name="ConsolePlugin", plugin_type="generic")
    class ConsolePlugin(AicPlugin):
        @classmethod
        def connect(cls):
            print("[ConsolePlugin] connected")
"""

from ..config import vprint
from .plugin_manager import PluginManager


def aic_plugin(name: str, plugin_type: str = "generic"):
    """
    Decorator that registers an AIC plugin with the framework.

    Args:
        name: Unique plugin name used by control apps in required_plugins.
        plugin_type: Category string — "storage", "model_registry",
                     "monitoring", or "generic".
    """
    def wrapper(cls):
        cls.u_name = name
        cls.plugin_type = plugin_type
        PluginManager.register(name, cls)
        vprint(f"[PluginFramework] Registered plugin '{name}' (type: {plugin_type})")
        return cls

    return wrapper
