Registration Service API
========================

The ai_nn_controller registration service maintains the registry of network nodes and
AI control applications.

RegisterInterface
-----------------

.. py:class:: register.RegisterInterface

   Central registration interface for the ai_nn_controller framework.

   This class manages registration of network nodes and AI applications,
   maintains state in Redis, and handles REQ/REP communication.

   **Initialization:**

   .. py:method:: __init__()

      Initialize the registration interface:

      - Load configuration from ``register.conf``
      - Connect to Redis
      - Bind ZMQ REP socket for registrations

   **Network Node Methods:**

   .. py:method:: register_network_node(node_id)

      Register a new network node.

      :param node_id: Unique node identifier
      :raises Exception: If node already registered

   .. py:method:: register_available_pms(node_id, available_pms)

      Register available performance measurements for a node.

      :param node_id: Node identifier
      :param available_pms: List of available PM names
      :raises Exception: If node not registered

   .. py:method:: register_available_ctrls(node_id, available_ctrls)

      Register available control functions for a node.

      :param node_id: Node identifier
      :param available_ctrls: List of available control function names
      :raises Exception: If node not registered

   .. py:method:: get_network_nodes()

      Get list of all registered network node IDs.

      :returns: List of registered node IDs

   .. py:method:: get_list_of_pm()

      Get all registered performance measurements.

      :returns: Dict mapping node_id to list of PM names

   .. py:method:: get_list_of_ctrl()

      Get all registered control functions.

      :returns: Dict mapping node_id to list of control names

   **AI Application Methods:**

   .. py:method:: register_ai_app(node_id)

      Register an AI application.

      :param node_id: Application identifier
      :raises Exception: If already registered (logs warning, doesn't fail)

   .. py:method:: register_ai_app_actions(node_id, network_node_list, list_of_pm, list_of_ctrl)

      Register AI app's measurement and control access.

      :param node_id: Application identifier
      :param network_node_list: List of node IDs the app wants to access
      :param list_of_pm: Dict mapping node_id to list of PM names
      :param list_of_ctrl: Dict mapping node_id to list of control names
      :raises Exception: If app not registered or requested access not available

   **Health Monitoring:**

   .. py:method:: alive_network_node_update(node_id)

      Update heartbeat for a network node.

      :param node_id: Node identifier
      :raises Exception: If node not registered

   .. py:method:: check_if_network_node_is_alive(node_id)

      Check if a node is still alive, unregister if not.

      :param node_id: Node identifier
      :raises Exception: If node not responding or not registered

   **Communication:**

   .. py:method:: read_msg()

      Read a message from the ZMQ socket.

      :returns: Parsed JSON message dict

   .. py:method:: send_msg(msg)

      Send a message on the ZMQ socket.

      :param msg: Message dict to send

Registration Protocol
---------------------

Node Registration
~~~~~~~~~~~~~~~~~

.. code-block:: text

   1. Node → Register: {"node_type": "network_node", "node_id": 3, "msg_type": "register"}
   2. Register → Node: {"msg_type": "ack", "node_id": 0}
   3. Node → Register: {"msg_type": "pm_availability", "node_id": 3, "available_pms": [...]}
   4. Register → Node: {
        "msg_type": "ack",
        "databus_ip": "node_msg_broker",
        "send_pm_port": "5555",
        "recv_command_port": "5557"
      }

App Registration
~~~~~~~~~~~~~~~~

.. code-block:: text

   1. App → Register: {"node_type": "aic_app", "node_id": -1, "msg_type": "register"}
   2. Register → App: {
        "msg_type": "ack",
        "network_node_list": [...],
        "list_of_pm": {...},
        "list_of_ctrl": {...}
      }
   3. App → Register: {
        "msg_type": "pm_ctrl_req",
        "node_id": -1,
        "network_node_list": [3, 8],
        "list_of_pm": {3: ["gain"], 8: ["preamp_gain"]},
        "list_of_ctrl": {8: ["SET_GAIN"]}
      }
   4. Register → App: {
        "msg_type": "ack",
        "databus_ip": "node_msg_broker",
        "ai_app_listen_port": "5554",
        "ai_app_send_command_port": "5556"
      }

Message Templates
-----------------

.. code-block:: python

   # Node registration acknowledgment
   network_node_registration_ack = {
       'msg_type': 'ack',
       'node_id': 0
   }

   # PM availability acknowledgment
   network_node_pm_availability_ack = {
       'msg_type': 'ack',
       'node_id': 0,
       'databus_ip': '',
       'send_pm_port': '',
       'recv_command_port': ''
   }

   # AI app registration acknowledgment
   ai_app_registration_ack = {
       'msg_type': 'ack',
       'node_id': 0,
       'network_node_list': [],
       'list_of_pm': {},
       'list_of_ctrl': {}
   }

   # AI app access acknowledgment
   ai_app_access_ack = {
       'msg_type': 'ack',
       'node_id': 0,
       'databus_ip': '',
       'ai_app_listen_port': '',
       'ai_app_send_command_port': ''
   }

   # Error message
   err = {
       'msg_type': 'err',
       'node_id': 0,
       'msg_content': ''
   }

Redis Data Structure
--------------------

.. list-table:: Redis Keys
   :header-rows: 1
   :widths: 50 50

   * - Key Pattern
     - Description
   * - ``network_nodes:network_node_list``
     - Set of registered node IDs
   * - ``network_nodes:network_node_pm_list:{node_id}``
     - Set of available PMs for node
   * - ``network_nodes:network_node_ctrl_list:{node_id}``
     - Set of available controls for node
   * - ``network_nodes:network_node_list:{node_id}``
     - Heartbeat counter for node
   * - ``ai_apps:ai_apps_list``
     - Set of registered AI app IDs
   * - ``ai_apps:ai_apps_info_list:{node_id}``
     - JSON with app configuration

Configuration
-------------

``register.conf`` format:

.. code-block:: ini

   registration_ip_address = aic_register
   ip_address = 0.0.0.0
   databus_ip_address = node_msg_broker
   recv_measurements = 5555
   pub_measurements = 5554
   recv_commands = 5556
   pub_commands = 5557
   register_sub = 5558
   register_pub = 5559
