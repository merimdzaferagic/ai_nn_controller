# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
PluginManager — runtime registry of loaded plugin classes.

Analogous to AicManager for control applications. Stores callable plugin
class references so the controller and control apps can look them up by name.

Discovery metadata is handled separately by PluginRegistry (plugins/registry.py).
"""

from typing import Dict, List, Optional, Type

from .AicPlugin import AicPlugin


class PluginManager:
    _plugins: Dict[str, Type[AicPlugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_class: Type[AicPlugin]) -> None:
        if name in cls._plugins:
            raise RuntimeError(f"A plugin named '{name}' is already registered.")
        cls._plugins[name] = plugin_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[AicPlugin]]:
        return cls._plugins.get(name)

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._plugins

    @classmethod
    def list_plugins(cls, plugin_type: Optional[str] = None) -> List[str]:
        if plugin_type:
            return [n for n, p in cls._plugins.items()
                    if getattr(p, "plugin_type", None) == plugin_type]
        return list(cls._plugins.keys())

    @classmethod
    def all_plugins(cls) -> Dict[str, Type[AicPlugin]]:
        return dict(cls._plugins)
