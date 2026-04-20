# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CompatibilityRange:
    min_version: str = "1.0.0"
    max_version: str = "2.x"


@dataclass
class CapabilityMetadata:
    name: str
    plugin_type: str
    schema: str = "urn:ai-nnc:capability:1"
    version: str = "1.0.0"
    compatibility: CompatibilityRange = field(default_factory=CompatibilityRange)
    capabilities: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "plugin_type": self.plugin_type,
            "schema": self.schema,
            "version": self.version,
            "compatibility": {
                "min": self.compatibility.min_version,
                "max": self.compatibility.max_version,
            },
            "capabilities": list(self.capabilities),
            "extra": dict(self.extra),
        }
