Message Broker API
==================

The ai_nn_controller message broker routes measurements from nodes to applications and
commands from applications to nodes.

UnifiedMeasurementBroker
------------------------

.. py:class:: node_msg_broker.UnifiedMeasurementBroker(context, recv_port=5555, send_port=5554)

   Broker that receives measurements from nodes and publishes to applications.

   Pattern: ``Nodes PUSH → Broker PULL → Broker PUB → Apps SUB``

   :param context: ZMQ context
   :param recv_port: Port to receive measurements (PULL socket)
   :param send_port: Port to publish measurements (PUB socket)

   **Methods:**

   .. py:method:: run()

      Start the forwarding loop. Receives from any node and publishes to all subscribers.

CommandBroker
-------------

.. py:class:: node_msg_broker.CommandBroker(context, recv_port=5556, send_port=5557)

   Broker for command messages from applications to nodes.

   Pattern: ``Apps PUSH → Broker PULL → Broker PUB → Nodes SUB``

   :param context: ZMQ context
   :param recv_port: Port to receive commands (PULL socket)
   :param send_port: Port to publish commands (PUB socket)

   **Methods:**

   .. py:method:: run()

      Start the command forwarding loop.

Port Configuration
------------------

.. list-table:: Broker Ports
   :header-rows: 1
   :widths: 15 15 20 50

   * - Port
     - Socket
     - Direction
     - Purpose
   * - 5554
     - PUB
     - → Apps
     - Measurement publication
   * - 5555
     - PULL
     - ← Nodes
     - Measurement collection
   * - 5556
     - PULL
     - ← Apps
     - Command collection
   * - 5557
     - PUB
     - → Nodes
     - Command publication

Message Format
--------------

All messages use the format::

    "{topic};{MessageEnvelope_JSON}"

Where:

- ``topic`` = node_id as string — used by ZMQ PUB/SUB for routing
- ``MessageEnvelope_JSON`` = JSON-serialised ``MessageEnvelope`` object

The ``MessageEnvelope`` (defined in ``ai_nn_controller/protocol/envelope.py``) is the
authoritative wire schema (``urn:ai-nnc:envelope:1``):

.. code-block:: json

   {
     "schema": "urn:ai-nnc:envelope:1",
     "version": "1.0",
     "message_type": "measurement",
     "source": "3",
     "target": "controller",
     "correlation_id": "<uuid4>",
     "lineage_id": "<uuid4>",
     "idempotency_key": "<uuid4>",
     "ts": 1741785600.123,
     "payload": {"amp1_target_gain": 20.5, "amp1_gain_tilt": 1.2}
   }

The ``payload`` field carries measurement data (for measurement messages) or command
parameters (for command messages). The ``idempotency_key`` on command messages is used
by nodes to deduplicate retried or duplicated commands.

Topic-Based Routing
-------------------

ZMQ PUB/SUB uses topic-based filtering:

- Publishers send: ``"{topic};{payload}"``
- Subscribers subscribe to topics: ``socket.setsockopt(zmq.SUBSCRIBE, b"3")``
- Only messages with matching topic prefix are delivered

This allows:

- Apps to subscribe only to nodes they care about
- Nodes to receive only commands addressed to them

Usage
-----

The broker is typically run as a standalone service:

.. code-block:: python

   import zmq
   from node_msg_broker import UnifiedMeasurementBroker, CommandBroker

   context = zmq.Context()

   # Create brokers
   meas_broker = UnifiedMeasurementBroker(context, recv_port=5555, send_port=5554)
   cmd_broker = CommandBroker(context, recv_port=5556, send_port=5557)

   # Start in threads
   import threading
   threading.Thread(target=meas_broker.run, daemon=True).start()
   threading.Thread(target=cmd_broker.run, daemon=True).start()

   # Keep main thread alive
   while True:
       time.sleep(1)

Or using the provided main function:

.. code-block:: bash

   python node_msg_broker.py

Architecture Diagram
--------------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────┐
   │                      MESSAGE BROKER                             │
   │                                                                 │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │              Measurement Flow                            │   │
   │  │                                                          │   │
   │  │   Node 3  ──┐                                            │   │
   │  │   Node 4  ──┼──► PULL:5555 ──► PUB:5554 ──┬──► App A    │   │
   │  │   Node 8  ──┘                             └──► App B    │   │
   │  │                                                          │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │              Command Flow                                │   │
   │  │                                                          │   │
   │  │   App A  ──┐                                             │   │
   │  │   App B  ──┼──► PULL:5556 ──► PUB:5557 ──┬──► Node 3    │   │
   │  │            │                              ├──► Node 4    │   │
   │  │            └                              └──► Node 8    │   │
   │  │                                                          │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘

Scaling Considerations
----------------------

The current broker design:

- Handles multiple nodes and apps
- Does not require configuration for specific nodes
- Nodes self-register by simply connecting

For high-throughput scenarios:

- Consider running multiple broker instances
- Use ZMQ ROUTER/DEALER for load balancing
- Implement message batching
