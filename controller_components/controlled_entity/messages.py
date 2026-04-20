# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
ZMQ message templates for the node registration protocol.

These templates define the message formats exchanged between
network nodes and the aic_register service.
"""

# Step 1: Register the node
register_node = {
    "node_type": "network_node",
    "node_id": -1,
    "msg_type": "register",
}

# Step 2: Declare available performance metrics
pm_availability = {
    "node_type": "network_node",
    "node_id": -1,
    "msg_type": "pm_availability",
    "available_pms": [],
}

# Step 3 (optional): Declare available control functions
ctrl_availability = {
    "node_type": "network_node",
    "node_id": -1,
    "msg_type": "ctrl_availability",
    "available_ctrls": [],
}

# Periodic heartbeat
alive = {
    "node_type": "network_node",
    "node_id": -1,
    "msg_type": "alive",
}
