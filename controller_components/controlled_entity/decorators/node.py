# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Node registration decorator for the controlled_entity framework.

Mirrors the @aic_app decorator from ai_nn_controller but for network nodes.
"""

from ..config import vprint

# Module-level registry (singleton -- one node per process)
_registered_node = None


def get_registered_node():
    """Return the registered node class, or None."""
    return _registered_node


def node(name):
    """
    Decorator that registers a ControlledEntity subclass with the framework.

    This decorator:
    1. Sets the u_name attribute on the class.
    2. Stores the class in the module-level registry for NodeRunner to find.
    3. Validates that required attributes are present.

    Each process can only register one node class (since each node runs
    in its own container).

    Args:
        name: Human-readable name for the node (e.g., "Amp1", "srsRAN").

    Usage:
        @node(name="Amp1")
        class Amp1Node(ControlledEntity):
            available_measurements = ["gain", "power"]

            def poll_measurements(self):
                return {"gain": 20.0, "power": -10.0}
    """

    def wrapper(cls):
        global _registered_node

        cls.u_name = name

        if not cls.available_measurements:
            raise ValueError(f"Node '{name}' must define available_measurements")

        if _registered_node is not None:
            raise RuntimeError(
                f"Only one node class can be registered per process. "
                f"'{name}' conflicts with '{_registered_node.u_name}'"
            )

        _registered_node = cls
        vprint(f"[controlled_entity] Registered node: {name}")

        return cls

    return wrapper
