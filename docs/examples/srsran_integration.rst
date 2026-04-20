srsRAN Integration Example
==========================

This example demonstrates how to integrate **ai_nn_controller** with a real wireless RAN
system — `srsRAN <https://www.srsran.com/>`_ — by bridging its InfluxDB metrics
server into the ai_nn_controller message bus. It highlights the framework's **multi-domain**
capability: the same controller that manages optical amplifiers and ROADMs can
simultaneously ingest live 5G RAN KPIs and expose them to AI agents.

Overview
--------

srsRAN ships with a metrics server that writes UE-level and system-level KPIs to
an InfluxDB bucket (the same data source Grafana dashboards use). The integration
adds two components:

1. **srsRAN Network Node** (``network_nodes/srsran_node/``) — polls InfluxDB for
   the latest metrics and pushes them into the ai_nn_controller message bus.
2. **A read-only control application** — subscribes to those measurements and
   exposes them via the REST API and MCP tools. See :ref:`srsran-read-app`.

.. code-block:: text

   ┌──────────────┐       ┌──────────────┐       ┌──────────────────────────┐
   │   srsRAN     │       │              │       │    ai_nn_controller Message Bus   │
   │  gNodeB /    │──────►│   InfluxDB   │◄──────│                          │
   │   Metrics    │ write │              │ poll  │  srsRAN Node (ID=10)     │
   │   Server     │       └──────────────┘       │    │                     │
   └──────────────┘                              │    ▼ PUSH measurements   │
                                                 │  Broker ──► PUB          │
                                                 │              │           │
                                                 │    ┌─────────▼────────┐  │
                                                 │    │ SrsranReadMeasure │  │
                                                 │    │   ments App      │  │
                                                 │    │ (SUB, REST, MCP) │  │
                                                 │    └──────────────────┘  │
                                                 └──────────────────────────┘

Available Metrics
-----------------

The srsRAN node exposes two categories of measurements:

**UE-Level Metrics** (from ``ue_info`` InfluxDB measurement):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Metric
     - Description
   * - ``pci``
     - Physical Cell ID
   * - ``rnti``
     - Radio Network Temporary Identifier
   * - ``dl_bitrate``
     - Downlink bitrate
   * - ``ul_bitrate``
     - Uplink bitrate
   * - ``dl_bler``
     - Downlink Block Error Rate
   * - ``ul_bler``
     - Uplink Block Error Rate
   * - ``dl_mcs``
     - Downlink Modulation and Coding Scheme
   * - ``ul_mcs``
     - Uplink Modulation and Coding Scheme
   * - ``dl_nof_ok`` / ``dl_nof_nok``
     - Downlink successful / failed transmissions
   * - ``ul_nof_ok`` / ``ul_nof_nok``
     - Uplink successful / failed transmissions
   * - ``bsr``
     - Buffer Status Report
   * - ``cqi``
     - Channel Quality Indicator
   * - ``ri``
     - Rank Indicator
   * - ``ul_snr``
     - Uplink SNR
   * - ``pusch_snr_db``
     - PUSCH SNR (dB)
   * - ``pucch_snr_db``
     - PUCCH SNR (dB)

**System-Level Metrics** (from ``app_resource_usage`` InfluxDB measurement):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Metric
     - Description
   * - ``cpu_usage_percent``
     - CPU usage of the srsRAN process
   * - ``memory_usage_MB``
     - Memory consumption (MB)
   * - ``power_consumption_Watts``
     - Estimated power consumption (W)

srsRAN Network Node
-------------------

The node (``network_nodes/srsran_node/node.py``) is built on the ``controlled_entity``
framework -- the same base class and decorator pattern used by the dummy nodes. The
key difference is the ``setup()`` hook, which initializes an InfluxDB poller thread
that queries the srsRAN metrics bucket.

This demonstrates how to integrate a real external data source using the
``ControlledEntity`` abstraction. The node developer only implements the southbound
logic; all ZMQ plumbing is handled by ``NodeRunner``.

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import threading

   @node(name="srsRAN")
   class SrsranNode(ControlledEntity):
       available_measurements = [
           "session_id",
           "pci", "rnti", "dl_bitrate", "ul_bitrate",
           "dl_bler", "ul_bler", "cqi", "ul_snr",
           "cpu_usage_percent", "memory_usage_MB",
           # ... full list in source
       ]
       measurement_interval = 1.0

       def setup(self):
           """Start InfluxDB poller thread -- runs after registration."""
           self._latest_metrics = {}
           self._metrics_lock = threading.Lock()
           self._influx_url = self.config.get("influxdb_url", "http://influxdb:8086")
           self._influx_bucket = self.config.get("influxdb_bucket", "srsran")
           thread = threading.Thread(target=self._poll_influxdb, daemon=True)
           thread.start()

       def poll_measurements(self):
           with self._metrics_lock:
               current = dict(self._latest_metrics)
           if current:
               current["session_id"] = f"session_{self.config['node_id']}_{int(time.time())}"
               return current
           return None

   if __name__ == "__main__":
       NodeRunner().run()

**Configuration** (``node.conf``):

.. code-block:: ini

   ip_address = aic_register
   register_port = 5558
   node_id = 10
   pub_port = 5580

   # InfluxDB connection (must match srsRAN metrics-server config)
   influxdb_url = http://influxdb:8086
   influxdb_token = <your-token>
   influxdb_org = srs
   influxdb_bucket = srsran

   poll_interval = 1

All custom keys (``influxdb_url``, ``influxdb_bucket``, etc.) are accessible via
``self.config`` in the node's ``setup()`` method.

**How it works:**

1. ``@node(name="srsRAN")`` registers the class with the ``controlled_entity`` framework
2. ``NodeRunner().run()`` handles registration with ``aic_register`` as node ID 10
3. After registration, ``setup()`` initializes the InfluxDB connection and starts a
   background poller thread
4. The poller queries two InfluxDB measurements: ``ue_info`` and ``app_resource_usage``
5. ``poll_measurements()`` returns the cached metrics every ``measurement_interval`` seconds
6. ``NodeRunner`` publishes the measurements to the broker via ZMQ PUSH

.. code-block:: python

   # Core InfluxDB query (from node.py)
   ue_query = f'''
       from(bucket: "{self.influxdb_bucket}")
           |> range(start: -30s)
           |> filter(fn: (r) => r._measurement == "ue_info")
           |> last()
   '''

.. _srsran-read-app:

srsRAN Read Measurements App
-----------------------------

The read-only control application subscribes to all srsRAN node metrics and
prints them. This follows exactly the same pattern as any other ai_nn_controller app:

.. code-block:: python

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController

   @aic_app(name="SrsranReadMeasurements")
   class SrsranReadMeasurementsApp(AicApp):
       aic_app_id = 10
       control_loop_update_time = 2

       # Subscribe to all srsRAN metrics from node 10
       read_measurements = {
           10: [
               "session_id",
               "pci", "rnti",
               "dl_bitrate", "ul_bitrate",
               "dl_bler", "ul_bler",
               "dl_mcs", "ul_mcs",
               "dl_nof_ok", "dl_nof_nok",
               "ul_nof_ok", "ul_nof_nok",
               "bsr", "cqi", "ri",
               "ul_snr", "pusch_snr_db", "pucch_snr_db",
               "cpu_usage_percent", "memory_usage_MB",
               "power_consumption_Watts",
           ],
       }

       # Read-only -- no control functions
       control_functions = {}

       @classmethod
       def process(cls, measurements):
           latest = measurements.get(10, [None])[-1] if measurements.get(10) else None
           if not latest:
               print("No srsRAN data yet")
               return

           print(f"DL bitrate : {latest.get('dl_bitrate')}")
           print(f"CQI        : {latest.get('cqi')}")
           print(f"CPU usage  : {latest.get('cpu_usage_percent')}%")

   if __name__ == "__main__":
       AicController(with_api=True).run()

Because this app is registered with the framework, the following are
auto-generated:

- **REST endpoint**: ``GET /apps/SrsranReadMeasurements/measurements``
- **MCP tool**: ``SrsranReadMeasurements_get_measurements``

This means an AI agent can query live 5G RAN KPIs via MCP alongside optical
network metrics, all from the same controller.

Docker Deployment
-----------------

The srsRAN node is defined in ``network_nodes/srsran_node/`` and requires an
active srsRAN deployment with InfluxDB. To add it to your stack, add the
following to ``docker-compose.yml``:

.. code-block:: yaml

   srsran_node:
     container_name: srsran_node
     build:
       context: ./network_nodes/srsran_node/
       dockerfile: Dockerfile
     depends_on:
       - aic_register
       - node_msg_broker
     networks:
       - aic_network
       - docker_metrics   # Access InfluxDB on the srsRAN metrics network
     command: >
       sh -c "sleep 5 && python3 node.py"

   srsran_reader:
     container_name: srsran_reader
     build:
       context: ./
       dockerfile: control_applications/srsran_read_measurements/Dockerfile
     ports:
       - "8000:8000"
     networks:
       - aic_network
     command: >
       sh -c "sleep 25 && pip install --no-cache-dir /ai_nn_controller && python3 aic_app.py --verbose"

   networks:
     docker_metrics:
       external: true   # Created by the srsRAN docker-compose

.. note::

   The ``docker_metrics`` network must already exist (created by the srsRAN
   Docker Compose stack). This allows the srsRAN node container to reach
   InfluxDB on its internal network.

Expected Output
---------------

When running, the srsRAN reader app prints measurements every 2 seconds:

.. code-block:: text

   ======================================================================
   [srsRAN Measurements] Processing at 1707609600.00
   ======================================================================
     session_id             : session_10_1707609600

     --- UE-Level Metrics ---
     pci                    : 1.0
     rnti                   : 17921.0
     dl_bitrate             : 28500000.0
     ul_bitrate             : 12300000.0
     dl_bler                : 0.02
     ul_bler                : 0.01
     dl_mcs                 : 27.0
     ul_mcs                 : 22.0
     cqi                    : 15.0
     ri                     : 2.0
     ul_snr                 : 25.3
     pusch_snr_db           : 24.8
     pucch_snr_db           : 23.1

     --- System-Level Metrics ---
     cpu_usage_percent      : 45.2
     memory_usage_MB        : 512.0
     power_consumption_Watts: 35.0
   ======================================================================

Key Patterns Demonstrated
-------------------------

1. **controlled_entity abstraction**: The srsRAN node is a ``ControlledEntity``
   subclass, just like the dummy nodes. The only difference is the ``setup()``
   hook that initializes the InfluxDB connection -- all ZMQ plumbing is handled
   by ``NodeRunner``
2. **External data-source bridging**: The ``setup()`` pattern can be used for any
   external telemetry source (Prometheus, SNMP, gRPC streaming, REST APIs, etc.)
3. **Read-only apps**: Not every app needs control functions; pure monitoring
   apps expose data via REST and MCP without sending commands
4. **Multi-domain integration**: The same controller simultaneously manages
   optical nodes (amplifiers, ROADMs) and wireless nodes (srsRAN gNodeB),
   demonstrating cross-domain network intelligence
5. **Docker network bridging**: The ``docker_metrics`` external network lets the
   srsRAN node reach InfluxDB without exposing it on the host

Next Steps
----------

- Add ``@agent_controlled`` operations to let an AI agent trigger RAN
  optimizations based on live KPIs (e.g., adjust scheduling weights when
  CQI drops)
- Build a cross-domain app that correlates optical link quality with RAN
  throughput
- Connect additional domain nodes (core network, transport) to create a
  fully converged multi-domain AI controller
