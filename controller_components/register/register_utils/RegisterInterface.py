# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Registration Interface Module.

This module provides the RegisterInterface class which serves as the central
registration service for the ai_nn_controller framework.
It maintains registration information for both network nodes and AI applications
using Redis for persistent storage.

The framework is domain-agnostic and supports any type of network node including
optical, wireless, RAN, core network, and more.

The registration service is a critical component that:
- Tracks all registered network nodes and their capabilities
- Manages AI application registrations and their access permissions
- Validates that requested measurements and control functions are available
- Monitors node health through alive/heartbeat mechanisms
- Returns broker connection information to registered entities

Architecture:
    Network nodes and AIC applications register through a REQ/REP ZMQ pattern.
    State is persisted in Redis, enabling the service to survive restarts.
"""

from .parse_config import parse_config
from .setup import check_entropy
import zmq
import json
import redis


class RegisterInterface:
    """
    Central registration interface for the ai_nn_controller framework.

    This class manages the registration of network nodes and AI applications,
    maintains their state in Redis, and handles the REQ/REP communication
    pattern for registration requests.

    Attributes:
        config (dict): Configuration loaded from register.conf
        sub_socket (str): ZMQ REP socket address for receiving registrations
        redis_db (Redis): Redis client for persistent state storage
        network_node_namespace (str): Redis namespace for network node data
        ai_app_namespace (str): Redis namespace for AI application data

    Redis Data Structure:
        - network_nodes:network_node_list - Set of registered node IDs
        - network_nodes:network_node_pm_list:{node_id} - Set of available PMs for node
        - network_nodes:network_node_ctrl_list:{node_id} - Set of available controls
        - ai_apps:ai_apps_list - Set of registered AI app IDs
        - ai_apps:ai_apps_info_list:{node_id} - JSON with app configuration
    """

    def __init__(self):
        # read configuration file
        self.config = parse_config('./register.conf')
        self.sub_socket = "tcp://" + self.config["ip_address"] + ":" + self.config["register_sub"]
        # self.pub_socket = "tcp://" + self.config["ip_address"] + ":" + self.config["register_pub"]

        # check entropy before establishing the connection with the databus
        check_entropy()

       # Connect to the Redis server
        self.redis_db = redis.Redis(host='redis', port=6379, decode_responses=True)
        # Create namespaces for different tables
        self.network_node_namespace = 'network_nodes'
        self.network_node_list = 'network_node_list'
        self.network_node_pm_list = 'network_node_pm_list'
        self.network_node_ctrl_list = 'network_node_ctrl_list'
        self.ai_app_namespace = 'ai_apps'
        self.ai_apps_list = 'ai_apps_list'
        self.ai_apps_info_list = 'ai_apps_info_list'

        print("Connecting to the databus****************")
        # connect to the databus pub and sub sockets
        self.connect()

    def connect(self):
        self.context = zmq.Context()
        #  Socket to talk to server
        print("Connecting to the databus")
        # self.consumer = self.context.socket(zmq.SUB)
        self.consumer = self.context.socket(zmq.REP)
        self.consumer.bind(self.sub_socket)
        self.consumer.setsockopt(zmq.LINGER, 0)
        # self.consumer.setsockopt(zmq.SUBSCRIBE,b"")
        self.consumer.setsockopt(zmq.CONFLATE, 1)

        # self.producer = self.context.socket(zmq.PUSH)
        # self.producer.connect(self.pub_socket)

    def get_network_nodes(self):
        registered_cells = list(self.redis_db.smembers(f'{self.network_node_namespace}:{self.network_node_list}'))
        return registered_cells
    #     return self.registered_cells

    def get_list_of_pm(self):
        registered_cells_pm = {}
        namespace_keys = list(self.redis_db.keys(f'{self.network_node_namespace}:{self.network_node_pm_list}*'))
        for network_node_n in namespace_keys:
            node_id_str = network_node_n.split(":")[-1]
            registered_cells_pm[int(node_id_str)] = list(self.redis_db.smembers(network_node_n))
        return registered_cells_pm

        # if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_pm_list}:{network_node_n}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_pm_list}:{network_node_n}', int(network_node_n)):
        # my_set = r.smembers('my-set')
        # return self.registered_cells_pm

    def get_list_of_ctrl(self):
        registered_ctrl = {}
        namespace_keys = list(self.redis_db.keys(f'{self.network_node_namespace}:{self.network_node_ctrl_list}*'))
        for network_node_n in namespace_keys:
            node_id_str = network_node_n.split(":")[-1]
            registered_ctrl[int(node_id_str)] = list(self.redis_db.smembers(network_node_n))
        return registered_ctrl
    #     return self.registered_cells_ctrl

    def read_msg(self):
        print("(******tying to receive******)")
        recv_msg = self.consumer.recv()
        print(recv_msg.decode("utf-8"))
        return json.loads(recv_msg.decode("utf-8"))
        # return self.consumer.recv_json()
        # return json.loads(self.consumer.recv().decode("utf-8"))
        # return self.consumer.recv().decode("utf-8")

    def send_msg(self, msg):
        msg = json.dumps(msg).encode("utf-8")
        self.consumer.send(msg)
        print("Command sent")

    def register_ai_app(self, node_id):
        if self.redis_db.exists(f'{self.ai_app_namespace}:{self.ai_apps_list}'):
            if self.redis_db.sismember(f'{self.ai_app_namespace}:{self.ai_apps_list}', int(node_id)):
                print(f"ai_app {node_id} already registered. Proceeding.")
                return
                # raise Exception("ai_app already registered")
        # if int(node_id) in self.registered_ai_apps:
            # raise Exception("ai_app already registered")
        # self.registered_ai_apps.append(int(node_id))
        self.redis_db.sadd(f'{self.ai_app_namespace}:{self.ai_apps_list}', int(node_id))
        # print(self.redis_db.smembers(f'{self.ai_app_namespace}:{self.ai_apps_list}'))



    def register_ai_app_actions(self, node_id, network_node_list, list_of_pm, list_of_ctrl):
        """
        Register AI app actions with validation.

        Args:
            node_id: The AI app's node ID
            network_node_list: List of network node IDs the app wants to control
            list_of_pm: Dict keyed by node_id with list of measurements per node
                       Example: {3: ["session_id", "amp1_gain"], 4: ["roadm1_gain"], ...}
            list_of_ctrl: List of control handles the app wants to use
        """
        if not self.redis_db.exists(f'{self.ai_app_namespace}:{self.ai_apps_list}') or not self.redis_db.sismember(f'{self.ai_app_namespace}:{self.ai_apps_list}', int(node_id)):
            raise Exception("ai_app not registered")

        # Validate all network nodes are registered
        for network_node_n in network_node_list:
            if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(network_node_n)):
                raise Exception("E2 node " + str(network_node_n) + " not registered with the near-RT RIC!")

        # Validate PMs - list_of_pm is now a dict keyed by node_id
        if isinstance(list_of_pm, dict):
            # Dict format: {node_id: [pm1, pm2, ...], ...}
            for pm_node_id, pm_list in list_of_pm.items():
                pm_node_id = int(pm_node_id)
                # Verify the node is in the requested network_node_list
                if pm_node_id not in network_node_list:
                    raise Exception(f"Node {pm_node_id} in list_of_pm is not in network_node_list")
                # Verify each PM is available from that specific node
                for pm in pm_list:
                    if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_pm_list}:{pm_node_id}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_pm_list}:{pm_node_id}', pm):
                        raise Exception("The requested PM: " + str(pm) + " is not available from node: " + str(pm_node_id))
        else:
            # Legacy list format: check each PM against all nodes (backward compatibility)
            for pm in list_of_pm:
                for network_node_n in network_node_list:
                    if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_pm_list}:{network_node_n}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_pm_list}:{network_node_n}', pm):
                        raise Exception("The requested PM: " + str(pm) + " is not available from node: " + str(network_node_n))

        # Validate CTRLs - list_of_ctrl should be a dict keyed by node_id with list of control functions per node
        if isinstance(list_of_ctrl, dict):
            # Dict format: {node_id: [ctrl1, ctrl2, ...], ...}
            for ctrl_node_id, ctrl_list in list_of_ctrl.items():
                ctrl_node_id = int(ctrl_node_id)
                # Verify the node is in the requested network_node_list
                if ctrl_node_id not in network_node_list:
                    raise Exception(f"Node {ctrl_node_id} in list_of_ctrl is not in network_node_list")
                # Verify each control function is available from that specific node
                for ctrl in ctrl_list:
                    if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_ctrl_list}:{ctrl_node_id}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_ctrl_list}:{ctrl_node_id}', ctrl):
                        raise Exception("The requested CTRL handle: " + str(ctrl) + " is not available from node: " + str(ctrl_node_id))
        else:
            # Legacy list format: check each CTRL against all nodes (backward compatibility)
            for ctrl in list_of_ctrl:
                for network_node_n in network_node_list:
                    if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_ctrl_list}:{network_node_n}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_ctrl_list}:{network_node_n}', ctrl):
                        raise Exception("The requested CTRL handle: " + str(ctrl) + " is not available for node: " + str(network_node_n))

        # Store AI app info in Redis
        ai_app_info = {'network_nodes': network_node_list, 'pm': list_of_pm, 'ctrl': list_of_ctrl}
        # Store as JSON string since Redis sets don't support nested structures
        self.redis_db.set(f'{self.ai_app_namespace}:{self.ai_apps_info_list}:{int(node_id)}', json.dumps(ai_app_info))


    def register_network_node(self, node_id):
        if self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}'):
            if self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id)):
                raise Exception("E2 Node already registered")
        self.redis_db.sadd(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id))
        self.redis_db.set(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}', int(9))
        # print(self.redis_db.smembers(f'{self.ai_app_namespace}:{self.ai_apps_list}'))
        # if int(node_id) in self.registered_cells:
        #     raise Exception("E2 Node already registered")
        # self.registered_cells.append(int(node_id))

    def register_available_pms(self, node_id, available_pms):
        if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id)):
            raise Exception("E2 node not registered")
        # if int(node_id) not in self.registered_cells:
        #     raise Exception("E2 node not registered")
        self.redis_db.sadd(f'{self.network_node_namespace}:{self.network_node_pm_list}:{int(node_id)}', *available_pms)

        # self.registered_cells_pm[int(node_id)] = available_pms

    def register_available_ctrls(self, node_id, available_ctrls):
        """Register available control functions for a network node."""
        if not self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}') or not self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id)):
            raise Exception("E2 node not registered")
        self.redis_db.sadd(f'{self.network_node_namespace}:{self.network_node_ctrl_list}:{int(node_id)}', *available_ctrls)

    def send_command(self, msg):
        self.consumer.send(msg)
        # self.consumer.send_json(msg)
        # self.producer.send_string(command)
        print("Command sent")


    def alive_network_node_update(self, node_id):
        if self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}'):
            # print(str(self.redis_db.get(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}')))
            alive_value = int(self.redis_db.get(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}'))
            alive_value = 3
            self.redis_db.set(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}', alive_value)
            # if self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id)):
            #     raise Exception("E2 Node already registered")
        else:
            raise Exception("E2 Node was not registered")

    def check_if_network_node_is_alive(self, node_id):
        # print("Checking if e2 ", node_id, "is alive\n")
        if self.redis_db.exists(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}'):
            # print(str(self.redis_db.get(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}')))
            alive_value = int(self.redis_db.get(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}'))
            alive_value -= 1
            if alive_value < 0:
                self.redis_db.delete(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}')
                self.redis_db.srem(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id))
                raise Exception("E2 node is not available! UNREGISTERING: " + str(node_id))
            else:
                self.redis_db.set(f'{self.network_node_namespace}:{self.network_node_list}:{str(int(node_id))}', alive_value)
            # if self.redis_db.sismember(f'{self.network_node_namespace}:{self.network_node_list}', int(node_id)):
            #     raise Exception("E2 Node already registered")
        else:
            raise Exception("E2 node: " + str(node_id) + " is not registered!")


    # def __del__(self):
    #     self.producer.close()
    #     self.consumer.close()
    #     self.contex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t.term()
