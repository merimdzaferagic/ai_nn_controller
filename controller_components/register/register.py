# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from time import sleep
from register_utils.RegisterInterface import RegisterInterface
from register_utils import messages
import sys
import json
import threading
import traceback

AIC_ID = 0

def handle_ai_app_msg(handler, msg):
    """
    Handles messages from ai_app.

    :param handler: The handler object to send/receive messages
    :param msg: The message received from ai_app
    :return: None
    """
    # Handle registration message
    if msg['msg_type'] == "register":
        print("REGISTER ai_app: ", msg['node_id'])
        try:
            handler.register_ai_app(msg['node_id'])
            # Create ack message
            ack_msg = messages.ai_app_registration_ack.copy()
            ack_msg['node_id'] = AIC_ID
            ack_msg['network_node_list'] = handler.get_network_nodes()
            ack_msg['list_of_pm'] = handler.get_list_of_pm()
            ack_msg['list_of_ctrl'] = handler.get_list_of_ctrl()
            # Send ack to ai_app
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            traceback.print_exc()
            # Create error message
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            # Send error message to ai_app
            handler.send_msg(err_msg)

    # Handle PM/Ctrl request message
    elif msg['msg_type'] == 'pm_ctrl_req':
        print("PM CTRL REQUEST FOR Network NODE")
        print(f"pm_ctrl_req node_id={msg['node_id']}")
        print(f"  network_node_list: {msg['network_node_list']}")
        print(f"  list_of_pm: {msg['list_of_pm']}")
        print(f"  list_of_ctrl: {msg['list_of_ctrl']}")
        try:
            handler.register_ai_app_actions(msg['node_id'], msg['network_node_list'], msg['list_of_pm'], msg['list_of_ctrl'])
            ack_msg = messages.ai_app_access_ack.copy()
            ack_msg['node_id'] = AIC_ID
            ack_msg['databus_ip'] = handler.config['databus_ip_address']
            ack_msg['ai_app_listen_port'] = handler.config['pub_measurements']
            ack_msg['ai_app_send_command_port'] = handler.config['recv_commands']
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            traceback.print_exc()
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            handler.send_msg(err_msg)


def handle_network_node_msg(handler, msg):
    # register network_node node on near-RT ric and share information about available PMs and CTRL
    if msg['msg_type'] == 'register':
        print("REGISTER network_node node: ", msg['node_id'])
        try:
            handler.register_network_node(msg['node_id'])
            # create ack msg
            ack_msg = messages.network_node_registration_ack.copy()
            ack_msg['node_id'] = AIC_ID
            # send ack to ai_app
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            # create error message
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            # send error message to ai_app
            handler.send_msg(err_msg)
    # # register PMs and CTRL that the ai_app is accessing
    elif msg['msg_type'] == 'pm_availability':
        print("Network Nodes sharing available PMs")
        print("pm_availability", msg['node_id'], msg['available_pms'])
        try:
            handler.register_available_pms(msg['node_id'], msg['available_pms'])
            ack_msg = messages.network_node_pm_availability_ack.copy()
            ack_msg['node_id'] = AIC_ID
            ack_msg['databus_ip'] = handler.config['databus_ip_address']
            ack_msg['send_pm_port'] = handler.config['recv_measurements']
            ack_msg['recv_command_port'] = handler.config['pub_commands']
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            handler.send_msg(err_msg)
    elif msg['msg_type'] == 'ctrl_availability':
        print("Network Nodes sharing available Control Functions")
        print("ctrl_availability", msg['node_id'], msg['available_ctrls'])
        try:
            handler.register_available_ctrls(msg['node_id'], msg['available_ctrls'])
            ack_msg = messages.network_node_ctrl_availability_ack.copy()
            ack_msg['node_id'] = AIC_ID
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            handler.send_msg(err_msg)
    elif msg['msg_type'] == 'alive':
        print("Alive msg received from: ", msg['node_id'])
        try:
            handler.alive_network_node_update(msg['node_id'])
            # handler.register_network_node(msg['node_id'])
            # create ack msg
            ack_msg = messages.network_node_alive_ack.copy()
            ack_msg['node_id'] = AIC_ID
            # send ack to ai_app
            handler.send_msg(ack_msg)
        except Exception as e:
            print(e)
            # create error message
            err_msg = messages.err.copy()
            err_msg['node_id'] = AIC_ID
            err_msg['msg_content'] = str(e)
            # send error message to ai_app
            handler.send_msg(err_msg)


def handle_msg_arrival(handler, msg):
    print(msg)
    if msg['node_type'] in ['ai_app', 'aic_app']:
        handle_ai_app_msg(handler, msg)
    elif msg['node_type'] == 'network_node':
        handle_network_node_msg(handler, msg)
    else:
        print(f"Unknown node_type: {msg['node_type']}")
        # Must send a reply to satisfy ZMQ REP pattern
        err_msg = messages.err.copy()
        err_msg['node_id'] = AIC_ID
        err_msg['msg_content'] = f"Unknown node_type: {msg['node_type']}"
        handler.send_msg(err_msg)


register = RegisterInterface()


def handle_msgs():
    while True:
        handle_msg_arrival(register, register.read_msg())

def check_network_nodes_status():
    while True:
        try:
            for node_id in register.get_network_nodes():
                register.check_if_network_node_is_alive(node_id)
            sleep(2)
        except Exception as e:
            print(e)


if __name__=="__main__":
    threading.Thread(target=handle_msgs).start()
    threading.Thread(target=check_network_nodes_status).start()
