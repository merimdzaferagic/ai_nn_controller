# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Controlled Entity Framework for ai_nn_controller Network Nodes.

A framework for building network nodes that integrate with ai_nn_controller.
This is the node-side counterpart to the ai_nn_controller package.

Usage:
    from controlled_entity import ControlledEntity, node, NodeRunner

    @node(name="MyNode")
    class MyNode(ControlledEntity):
        available_measurements = ["gain", "power"]

        def poll_measurements(self):
            return {"gain": 20.0, "power": -10.0}

    NodeRunner().run()
"""

from .ControlledEntity import ControlledEntity
from .NodeRunner import NodeRunner
from .decorators.node import node
from .config import NodeConfig, vprint

__all__ = [
    "ControlledEntity",
    "NodeRunner",
    "node",
    "NodeConfig",
    "vprint",
]

__version__ = "1.0.0"
