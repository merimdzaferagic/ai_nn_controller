# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from typing import Dict, List, Optional

from .metadata import CapabilityMetadata


class PluginRegistry:
    _plugins: Dict[str, CapabilityMetadata] = {}

    @classmethod
    def register(cls, metadata: CapabilityMetadata) -> None:
        key = f"{metadata.plugin_type}:{metadata.name}"
        cls._plugins[key] = metadata

    @classmethod
    def discover(cls, plugin_type: Optional[str] = None) -> List[dict]:
        items = cls._plugins.values()
        if plugin_type:
            items = [m for m in items if m.plugin_type == plugin_type]
        return [m.to_dict() for m in items]
