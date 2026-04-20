Developing Network Nodes
=========================

This guide covers how to develop network nodes for **ai_nn_controller** using the
``controlled_entity`` package.

The ``controlled_entity`` package is the **node-side counterpart** to
``ai_nn_controller``. It provides a base class and execution engine that abstract
away all northbound ZMQ plumbing (registration, measurement publishing, command
ingestion, heartbeats). Node developers only implement the **southbound interface**:
how to get measurements from the device and how to apply commands to it.

Overview
--------

The framework is domain-agnostic. The same pattern works for any type of network
node — optical amplifiers, ROADMs, 5G RAN base stations, core network elements,
or anything else that produces telemetry or accepts control commands.

.. code-block:: text

   ┌──────────────────────────────────────────────────────────────┐
   │                    Your Node Code                            │
   │                                                              │
   │  @node(name="MyNode")                                        │
   │  class MyNode(ControlledEntity):                             │
   │      available_measurements = [...]                          │
   │                                                              │
   │      def poll_measurements(self):  ◄── Southbound (you)      │
   │          return {...}                                        │
   │                                                              │
   │      def handle_command(self, payload):  ◄── Southbound (you)│
   │          apply_to_device(payload)                            │
   │                                                              │
   │      def setup(self):  ◄── One-time init (optional)          │
   │          connect_to_hardware()                               │
   │                                                              │
   ├──────────────────────────────────────────────────────────────┤
   │                    NodeRunner (framework)                     │
   │                                                              │
   │  - Registration with aic_register      ◄── Northbound        │
   │  - PUSH measurements to broker             (framework)       │
   │  - SUB commands from broker                                  │
   │  - Alive heartbeats                                          │
   │  - Threading for all concurrent operations                   │
   └──────────────────────────────────────────────────────────────┘

Core Components
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Description
   * - ``ControlledEntity``
     - Base class for all network nodes. Subclass this and implement the southbound methods.
   * - ``@node(name="...")``
     - Decorator that registers a ``ControlledEntity`` subclass. Sets the node name and validates required attributes.
   * - ``NodeRunner``
     - Execution engine that handles all ZMQ communication. Instantiate and call ``.run()`` after defining your node class.

Import everything from the package:

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner

ControlledEntity Base Class
----------------------------

The base class defines the interface that all nodes must implement:

**Required attributes** (define in your subclass):

- ``available_measurements`` (list[str]): Names of performance metrics this node exposes. Must not be empty.
- ``measurement_interval`` (float): Seconds between measurement polls. Default: ``1.0``.

**Optional attributes**:

- ``available_controls`` (list[str]): Control function names (e.g., ``["SET_GAIN", "SET_VOA"]``). Default: ``[]`` (measurement-only node).

**Auto-injected attributes** (set by the framework):

- ``u_name`` (str): Human-readable name, set by the ``@node`` decorator.
- ``config`` (dict): Parsed from ``node.conf``, injected by ``NodeRunner`` before ``setup()`` is called.

**Southbound methods** (implement in your subclass):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Description
   * - ``poll_measurements() -> dict | None``
     - **Required.** Return current measurements as a dict, or ``None`` to skip this cycle.
   * - ``handle_command(payload: dict) -> bool``
     - **Optional.** Apply an incoming command. Return ``True`` on success, ``False`` otherwise. Only needed if ``available_controls`` is set.
   * - ``setup() -> None``
     - **Optional.** One-time initialization after registration. Use for connecting to external data sources, hardware, etc. ``self.config`` is available at this point.

The @node Decorator
-------------------

The ``@node`` decorator registers your class with the framework:

.. code-block:: python

   @node(name="Amp1")
   class Amp1Node(ControlledEntity):
       available_measurements = ["gain", "power"]
       ...

It performs three things:

1. Sets ``u_name`` on the class (used in log messages)
2. Validates that ``available_measurements`` is defined and non-empty
3. Stores the class in a module-level registry for ``NodeRunner`` to discover

**One node per process**: Each process (container) can only register one node class.
This is enforced by the decorator -- attempting to register a second class raises
``RuntimeError``.

NodeRunner
----------

The ``NodeRunner`` is the execution engine that handles all northbound communication:

.. code-block:: python

   if __name__ == "__main__":
       NodeRunner(config_file="./node.conf", verbose=False).run()

**Parameters**:

- ``config_file`` (str): Path to the node configuration file. Default: ``"./node.conf"``
- ``verbose`` (bool): Enable verbose logging. Default: ``False``

**What ``run()`` does**:

1. Connects to ``aic_register`` via REQ/REP
2. Registers the node (announces node ID)
3. Registers available PMs (declares ``available_measurements``, receives broker connection info)
4. Registers available controls (if any, declares ``available_controls``)
5. Connects PUSH socket to broker for measurement publishing
6. Connects SUB socket to broker for command listening (if controls defined)
7. Calls ``node.setup()``
8. Starts measurement publishing thread
9. Starts command listener thread (if applicable)
10. Runs alive heartbeat loop on main thread

Building a Measurement-Only Node
----------------------------------

The simplest node publishes measurements without accepting commands. See
``network_nodes/dummy_nodes/amp1_node/node.py`` for a complete working example:

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import random
   import time

   @node(name="Amp1")
   class Amp1Node(ControlledEntity):
       available_measurements = [
           "session_id",
           "amp1_target_gain",
           "amp1_gain_tilt",
           "amp1_target_power",
           "amp1_control_mode",
       ]
       measurement_interval = 1.0

       def poll_measurements(self):
           return {
               "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
               "amp1_target_gain": round(random.uniform(15.0, 25.0), 2),
               "amp1_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
               "amp1_target_power": round(random.uniform(0.0, 5.0), 2),
               "amp1_control_mode": 3,
           }

   if __name__ == "__main__":
       NodeRunner().run()

Key points:

- ``available_measurements`` declares the metric names this node will publish
- ``measurement_interval`` controls how often ``poll_measurements()`` is called
- ``self.config`` contains values parsed from ``node.conf`` (including ``node_id``)
- Return ``None`` from ``poll_measurements()`` to skip publishing for that cycle

Adding Command Handling
-----------------------

To accept commands from control applications, add ``available_controls`` and
implement ``handle_command()``. See ``network_nodes/dummy_nodes/roadm3_with_command/node.py``:

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import random
   import time

   @node(name="ROADM3")
   class ROADM3Node(ControlledEntity):
       available_measurements = [
           "session_id",
           "roadm3_preamp_target_gain",
           "roadm3_preamp_gain_tilt",
           "roadm3_booster_target_gain",
           "roadm3_booster_gain_tilt",
       ]
       available_controls = ["SET_GAIN", "SET_VOA", "SET_TILT"]
       measurement_interval = 5.0

       def poll_measurements(self):
           return {
               "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
               "roadm3_preamp_target_gain": round(random.uniform(17.0, 21.0), 2),
               "roadm3_preamp_gain_tilt": round(random.uniform(-1.5, 1.5), 2),
               "roadm3_booster_target_gain": round(random.uniform(14.0, 19.0), 2),
               "roadm3_booster_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
           }

       def handle_command(self, payload):
           """Process incoming commands from control applications."""
           print(f"[ROADM3] Processing command: {payload}")

           if "target_gain" in payload:
               print(f"[ROADM3] Setting target gain to: {payload['target_gain']}")

           if "preamp_gain" in payload:
               print(f"[ROADM3] Setting preamp gain to: {payload['preamp_gain']}")

           if "booster_gain" in payload:
               print(f"[ROADM3] Setting booster gain to: {payload['booster_gain']}")

           if "voa_mux" in payload:
               channel = payload.get("channel", "unknown")
               print(f"[ROADM3] Setting VOA MUX for channel {channel}: {payload['voa_mux']}")

           return True

   if __name__ == "__main__":
       NodeRunner().run()

When ``available_controls`` is set, the ``NodeRunner``:

- Registers the control functions with ``aic_register``
- Subscribes to the command topic on the broker (using the node's ID)
- Starts a command listener thread that dispatches to ``handle_command()``

The ``payload`` dict arrives as the JSON body sent by the control application via
``add_command()`` or the REST API.

Using the setup() Hook
-----------------------

For real-world nodes that connect to external systems, use the ``setup()`` method.
It runs once after registration completes and before the measurement/command loops
start. At this point ``self.config`` is available.

This is the pattern used by the srsRAN node (``network_nodes/srsran_node/node.py``):

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import threading
   import time

   @node(name="srsRAN")
   class SrsranNode(ControlledEntity):
       available_measurements = [
           "session_id",
           "dl_bitrate", "ul_bitrate",
           "cqi", "ul_snr",
           "cpu_usage_percent", "memory_usage_MB",
       ]
       measurement_interval = 1.0

       def setup(self):
           """Initialize InfluxDB connection after registration."""
           self._latest_metrics = {}
           self._metrics_lock = threading.Lock()

           # Read connection params from node.conf
           self._influx_url = self.config.get("influxdb_url", "http://influxdb:8086")
           self._influx_bucket = self.config.get("influxdb_bucket", "srsran")

           # Start background poller
           thread = threading.Thread(target=self._poll_influxdb, daemon=True)
           thread.start()

       def _poll_influxdb(self):
           """Background thread that queries InfluxDB."""
           while True:
               # ... query InfluxDB, update self._latest_metrics ...
               time.sleep(1)

       def poll_measurements(self):
           with self._metrics_lock:
               current = dict(self._latest_metrics)
           if current:
               current["session_id"] = f"session_{self.config['node_id']}_{int(time.time())}"
               return current
           return None

   if __name__ == "__main__":
       NodeRunner().run()

This pattern works for any external data source: REST APIs, gRPC streams, SNMP,
NETCONF, hardware interfaces, etc.

Node Configuration (node.conf)
------------------------------

Each node needs a ``node.conf`` file with at minimum:

.. code-block:: ini

   # Register address (Docker service name or IP)
   ip_address = aic_register

   # Registration port
   register_port = 5558

   # Unique node identifier -- must not conflict with other nodes
   node_id = 3

You can add any custom key-value pairs. They will be available in ``self.config``
after the framework parses the file:

.. code-block:: ini

   # Custom keys for your node
   influxdb_url = http://influxdb:8086
   influxdb_bucket = srsran
   poll_interval = 1

The parser auto-converts values to ``int`` or ``float`` where possible, otherwise
keeps them as strings.

Docker Deployment
-----------------

Each node runs in its own container. A typical Dockerfile:

.. code-block:: dockerfile

   FROM python:3.9-slim

   # Install the controlled_entity package
   COPY controller_components/controlled_entity/ /tmp/controlled_entity/
   RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

   WORKDIR /node

   # Copy node files
   COPY network_nodes/dummy_nodes/amp1_node/*.py ./
   COPY network_nodes/dummy_nodes/amp1_node/*.conf ./

   CMD ["python3", "node.py"]

Add to ``docker-compose.yml``:

.. code-block:: yaml

   amp1_node:
     container_name: amp1_node
     build:
       context: ./
       dockerfile: network_nodes/dummy_nodes/amp1_node/Dockerfile
     networks:
       - aic_network
     depends_on:
       - aic_register
       - node_msg_broker

Registration Protocol
---------------------

The ``NodeRunner`` handles the full registration protocol automatically. For
reference, the three-step handshake is:

.. code-block:: text

   Step 1: Register Node
   Node → Register: {"node_type": "network_node", "node_id": 3, "msg_type": "register"}
   Register → Node: {"msg_type": "ack", ...}

   Step 2: Declare Available PMs
   Node → Register: {"msg_type": "pm_availability", "node_id": 3,
                      "available_pms": ["gain", "power", ...]}
   Register → Node: {"msg_type": "ack", "databus_ip": "node_msg_broker",
                      "send_pm_port": "5555", "recv_command_port": "5557"}

   Step 3 (optional): Declare Available Controls
   Node → Register: {"msg_type": "ctrl_availability", "node_id": 3,
                      "available_ctrls": ["SET_GAIN", "SET_VOA"]}
   Register → Node: {"msg_type": "ack"}

After registration, the node connects to the broker using the addresses returned
in step 2.

Message Format
~~~~~~~~~~~~~~

All messages on the data bus use the format:

.. code-block:: text

   "{node_id};{json_payload}"

Example measurement: ``"3;{\"amp1_target_gain\": 20.5, \"amp1_gain_tilt\": 1.2}"``

Example command: ``"3;{\"target_gain\": 15.0}"``

Threading Model
~~~~~~~~~~~~~~~

``NodeRunner`` uses three threads:

- **Main thread**: Sends alive heartbeats every 2 seconds
- **Measurement thread**: Calls ``poll_measurements()`` at ``measurement_interval``, publishes via PUSH
- **Command thread** (if controls defined): Listens on SUB socket, dispatches to ``handle_command()``

Dummy Nodes Reference
---------------------

The ``network_nodes/dummy_nodes/`` directory contains complete working examples:

.. list-table::
   :header-rows: 1
   :widths: 25 10 30 35

   * - Node
     - ID
     - Measurements
     - Controls
   * - ``amp1_node``
     - 3
     - gain, tilt, power, mode
     - (none)
   * - ``amp2_node``
     - 5
     - gain, tilt, power, mode
     - (none)
   * - ``amp3_node``
     - 6
     - gain, tilt, power, mode
     - (none)
   * - ``roadm1_node``
     - 4
     - preamp/booster gain & tilt
     - (none)
   * - ``roadm2_node``
     - 7
     - preamp/booster gain & tilt
     - (none)
   * - ``roadm3_with_command``
     - 8
     - preamp/booster gain & tilt
     - SET_GAIN, SET_VOA, SET_TILT

These nodes generate simulated (random) data and are intended for testing and
development. Use them as templates when building real integrations.

Best Practices
--------------

1. **Keep poll_measurements() fast**: Avoid blocking I/O in the poll method. For slow data sources, use a background thread in ``setup()`` and cache results (see srsRAN pattern).
2. **Return None to skip**: If no data is available, return ``None`` from ``poll_measurements()`` instead of empty dicts.
3. **Use self.config for connection params**: Put external URLs, credentials, and tuning parameters in ``node.conf`` rather than hardcoding them.
4. **One node per container**: The framework enforces one ``@node`` class per process. Run each node in its own Docker container.
5. **Unique node IDs**: Each node must have a unique ``node_id`` across the entire deployment. Collisions will cause registration errors.

Next Steps
----------

- :doc:`developing_apps` - Build control applications that consume node measurements
- :doc:`commands` - Define commands that apps can send to nodes
- :doc:`../examples/dummy_node` - Step-by-step dummy node walkthrough
- :doc:`../examples/srsran_integration` - Real-world integration example
