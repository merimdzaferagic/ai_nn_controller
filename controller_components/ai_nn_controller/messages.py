# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

register_aic_app = {
        "node_type": "aic_app",
        "node_id": -1,
        "msg_type": "register"
        }

pm_ctrl_req = {
        "node_type": "aic_app",
        "node_id": -1,
        "msg_type": "pm_ctrl_req",
        'network_node_list': [],
        'list_of_pm': [],
        'list_of_ctrl': []
        }
