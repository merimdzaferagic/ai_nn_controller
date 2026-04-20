# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

# {node_type: "ai_app/e2/near-rt", node_id: int, message_type: "register/pm_ctrl_req/err_msg,ack", list_of_pm: [], list_of_ctrl: [], message_content: str}

ai_app_registration_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "ack",
        "network_node_list": [],
        "list_of_pm": {},
        "list_of_ctrl": {}
        }

ai_app_access_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "ack",
        "databus_ip": "",
        "ai_app_listen_port": "5554",
        "ai_app_send_command_port": "5556",
        "msg_content": "Actions Registered"
        }

network_node_registration_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "ack"
        }

network_node_pm_availability_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "databus_ip": "",
        "send_pm_port": "5555",
        "recv_command_port": "5557",
        "msg_type": "ack",
        "msg_content": "Available PMs Registered"
        }

network_node_ctrl_availability_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "ack",
        "msg_content": "Available Control Functions Registered"
        }

err = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "err_msg",
        "msg_content": ""
        }

network_node_alive_ack = {
        "node_type": "near-rt",
        "node_id": -1,
        "msg_type": "ack",
        "msg_content": ""
        }
