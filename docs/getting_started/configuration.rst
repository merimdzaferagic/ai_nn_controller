Configuration
=============

This guide covers the configuration options for **ai_nn_controller**.

Key Insight: Registration-Based Discovery
-----------------------------------------

**Nodes and AIC apps only need to know the register's address.** The register
returns the broker's address during the registration handshake. This means you
never need to configure broker addresses in nodes or applications — only the
single register address.

Configuration Files
-------------------

Register Configuration
~~~~~~~~~~~~~~~~~~~~~~

The register service (``controller_components/register/register.conf``) defines
the central configuration:

.. code-block:: ini

   # Register's own binding address
   registration_ip_address = aic_register
   ip_address = 0.0.0.0

   # Broker address (returned to registrants)
   databus_ip_address = node_msg_broker

   # Port mappings
   recv_measurements = 5555    # Nodes PUSH measurements here
   pub_measurements = 5554     # Apps SUB to measurements here
   recv_commands = 5556        # Apps PUSH commands here
   pub_commands = 5557         # Nodes SUB to commands here
   register_sub = 5558         # Registration port (REQ/REP)

AIC App Configuration
~~~~~~~~~~~~~~~~~~~~~

Apps only need to know the register address (``aic_app.conf``):

.. code-block:: ini

   ip_address = aic_register
   register_port = 5558

Node Configuration
~~~~~~~~~~~~~~~~~~

Nodes using the ``controlled_entity`` package need a ``node.conf`` file with
the register address and a unique node ID. The ``NodeRunner`` parses this file
and injects the values into ``self.config`` on the node instance.

**Required keys**:

.. code-block:: ini

   # Register address (Docker service name or IP)
   ip_address = aic_register

   # Registration port
   register_port = 5558

   # Unique node identifier — must not conflict with other nodes
   node_id = 3

**Optional / custom keys** — add any key-value pairs your node needs:

.. code-block:: ini

   # For srsRAN nodes (InfluxDB connection)
   influxdb_url = http://influxdb:8086
   influxdb_token = <your-token>
   influxdb_org = srs
   influxdb_bucket = srsran
   poll_interval = 1

   # For Twilight optical nodes
   twilight_url = http://host.docker.internal:8000
   device_name = Amp_ila1
   device_type = amplifier

Custom keys are accessible in the node's ``setup()`` and ``poll_measurements()``
methods via ``self.config``:

.. code-block:: python

   def setup(self):
       url = self.config.get("influxdb_url", "http://localhost:8086")

The parser auto-converts values to ``int`` or ``float`` where possible.
Lines starting with ``#`` are comments.

Port Summary
------------

.. list-table:: Port Allocations
   :header-rows: 1
   :widths: 10 20 15 15 40

   * - Port
     - Service
     - Socket Type
     - Direction
     - Purpose
   * - 5554
     - Broker
     - PUB
     - → Apps
     - Measurement publication
   * - 5555
     - Broker
     - PULL
     - ← Nodes
     - Measurement collection
   * - 5556
     - Broker
     - PULL
     - ← Apps
     - Command collection
   * - 5557
     - Broker
     - PUB
     - → Nodes
     - Command publication
   * - 5558
     - Register
     - REP
     - ↔ All
     - Registration (REQ/REP)
   * - 6379
     - Redis
     - TCP
     - ↔ Register
     - State storage
   * - 8000
     - AIC Server
     - HTTP
     - ↔ Clients
     - REST API & MCP

AicController Configuration
---------------------------

When instantiating ``AicController``, you can configure:

.. code-block:: python

   from ai_nn_controller.AicController import AicController

   controller = AicController(
       with_api=True,       # Enable FastAPI server
       api_host="0.0.0.0",  # API host address
       api_port=8000,       # API port
       verbose=True         # Enable verbose logging
   )
   controller.run()

Command-Line Arguments
~~~~~~~~~~~~~~~~~~~~~~

When running an app directly:

.. code-block:: bash

   python aic_app.py --verbose --port 8000 --host 0.0.0.0

Arguments:

- ``--verbose, -v``: Enable verbose output for debugging
- ``--port, -p``: Port for the FastAPI server (default: 8000)
- ``--host``: Host address for the FastAPI server (default: 0.0.0.0)

Environment Variables
---------------------

The following environment variables are recognised at runtime:

.. list-table:: Environment Variables
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Effect
   * - ``AIC_MAX_QUEUE_SIZE``
     - ``500``
     - Per-app per-topic measurement queue depth (controller side)
   * - ``AIC_ARBITRATION_STRATEGY``
     - ``last_write_wins``
     - Arbitrator strategy: ``last_write_wins`` or ``min_gap``
   * - ``NODE_MAX_PENDING_COMMANDS``
     - ``200``
     - Max pending commands + idempotency cache size on node side

Application Configuration
--------------------------

Within your application, configure via class attributes:

.. code-block:: python

   @aic_app(name="MyApp")
   class MyApp(AicApp):
       aic_app_id = 100

       # How often process() is called (seconds)
       control_loop_update_time = 2

       # Measurements to read per node
       read_measurements = {
           3: ["gain", "power", "temperature"],
           4: ["status", "alarm"],
           8: ["preamp_gain", "booster_gain"]
       }

       # Control functions per node
       control_functions = {
           3: ["SET_GAIN"],
           8: ["SET_GAIN", "SET_VOA", "SET_TILT"]
       }

       # cell_ids is auto-generated as the union of
       # read_measurements and control_functions keys: [3, 4, 8]

Next Steps
----------

- :doc:`../user_guide/developing_apps` — Create custom control applications
- :doc:`../user_guide/developing_nodes` — Build network nodes with controlled_entity
- :doc:`../user_guide/docker` — Docker deployment guide
- :doc:`../api/rest_api` — REST API configuration
