# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from .parse_config import parse_config
from .aic_setup import check_entropy
from .config import vprint
import zmq
import json
from . import messages

class RegisterAicApp:
    def __init__(self):
        # read configuration file
        self.config = parse_config('./aic_app.conf')
        self.socket = "tcp://" + self.config["ip_address"] + ":" + self.config["register_port"]

        # check entropy before establishing the connection with the databus
        check_entropy()

        vprint("Connecting to the RIC Registration****************: ", self.config["ip_address"], self.config["register_port"])
        # Databus connection info - will be populated from register response
        self.databus_ip = ""
        self.send_port = ""
        self.rcv_port = ""

        # connect to the databus pub and sub sockets
        self.connect()

    def get_broker_info(self):
        """
        Returns the broker connection info received from the register.
        Should be called after register_aic_app() has been called.

        Returns:
            dict: Contains 'databus_ip', 'listen_port', 'command_port'
        """
        return {
            'databus_ip': self.databus_ip,
            'listen_port': self.rcv_port,
            'command_port': self.send_port
        }

    def connect(self):
        self.context = zmq.Context()
        #  Socket to talk to server
        self.registration_handle = self.context.socket(zmq.REQ)
        self.registration_handle.connect(self.socket)

    def read_msg(self):
        recv_msg =  self.registration_handle.recv()
        recv_msg = json.loads(recv_msg.decode("utf-8"))
        return recv_msg

    def send_msg(self, msg):
        msg = json.dumps(msg).encode("utf-8")
        self.registration_handle.send(msg)
        vprint("Command sent")

    def register_aic_app(self, aic_app):
        reg_msg = messages.register_aic_app
        reg_msg['node_id'] = aic_app.aic_app_id
        self.send_msg(reg_msg)
        vprint("Registration message sent: ", aic_app.aic_app_id)

        reg_response = self.read_msg()
        vprint(reg_response)
        if reg_response["msg_type"] == "err_msg":
            raise RuntimeError("aic_app was not able to register with the near-RT RIC \n Error msg: %s " % reg_response["msg_content"])

        pm_ctrl_req = messages.pm_ctrl_req.copy()
        pm_ctrl_req["node_id"] = aic_app.aic_app_id
        pm_ctrl_req['network_node_list'] = aic_app.cell_ids

        # read_measurements must be a dict keyed by node_id with list of measurements per node
        # Example: {3: ["session_id", "amp1_gain"], 4: ["session_id", "roadm1_gain"], ...}
        if isinstance(aic_app.read_measurements, dict):
            pm_ctrl_req['list_of_pm'] = aic_app.read_measurements
        else:
            raise RuntimeError("read_measurements must be a dict keyed by node_id (cell_id)")

        # control_functions must be a dict keyed by node_id with list of control functions per node
        # Example: {8: ["SET_GAIN", "SET_VOA"], ...}
        if hasattr(aic_app, 'control_functions') and isinstance(aic_app.control_functions, dict):
            pm_ctrl_req['list_of_ctrl'] = aic_app.control_functions
        else:
            # Default to empty dict if not specified
            pm_ctrl_req['list_of_ctrl'] = {}

        self.send_msg(pm_ctrl_req)
        vprint("PM_CTRL_REQUEST SENT")

        pm_ctrl_response = self.read_msg()
        vprint(pm_ctrl_response)
        if pm_ctrl_response["msg_type"] == "err_msg":
            raise RuntimeError("aic_app was not able to register with the near-RT RIC \n Error msg: %s " % pm_ctrl_response["msg_content"])

        self.databus_ip = pm_ctrl_response["databus_ip"]
        self.send_port = pm_ctrl_response["ai_app_send_command_port"]
        self.rcv_port = pm_ctrl_response["ai_app_listen_port"]
