# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from .plugin_manager import PluginManager


def validate_app_plugins(app_class) -> None:
    """
    Raise RuntimeError if any plugin declared in app_class.required_plugins
    is not registered in PluginManager.

    Called by AicController after plugins are loaded but before apps start.
    """
    required = getattr(app_class, "required_plugins", [])
    if not required:
        return

    missing = [p for p in required if not PluginManager.has(p)]
    if missing:
        available = PluginManager.list_plugins()
        raise RuntimeError(
            f"App '{app_class.u_name}' requires plugins {missing} which are not registered. "
            f"Available plugins: {available if available else '(none)'}"
        )
