Architecture
============

This document describes the architecture of **ai_nn_controller**.

ai_nn_controller is domain-agnostic and supports any type of network node — optical,
wireless, RAN, core network, and more.

System Overview
---------------

ai_nn_controller is organised into three main planes:

1. **Control Plane**: AIC applications and the FastAPI server
2. **Registration Plane**: Central registry and Redis storage
3. **Data Plane**: ZeroMQ message broker for measurements and commands

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────────────────┐
   │                              CONTROL PLANE                                   │
   │  ┌─────────────────────────────────────────────────────────────────────┐   │
   │  │                     AIC Server (FastAPI)                             │   │
   │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                     │   │
   │  │  │NetworkApp1 │  │ NetworkApp2│  │ Conflict   │    ... more apps    │   │
   │  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                     │   │
   │  │        └───────────────┴───────────────┘                             │   │
   │  │                        │                                             │   │
   │  │              ┌─────────▼─────────┐                                   │   │
   │  │              │   AicController   │ ◄── Manages app lifecycle         │   │
   │  │              │(ai_nn_controller) │     Routes messages               │   │
   │  │              └─────────┬─────────┘     Sends commands                │   │
   │  │                        │                                             │   │
   │  │  REST API: /apps/*     │    MCP: /mcp/*                              │   │
   │  └────────────────────────┼─────────────────────────────────────────────┘   │
   │                           │                                                  │
   │                     Port 8000                                                │
   └───────────────────────────┼──────────────────────────────────────────────────┘

Control Plane Components
------------------------

AicController
~~~~~~~~~~~~~

The ``AicController`` is the runtime engine that:

- Manages application lifecycle (start, pause, stop)
- Connects to the message broker via ZeroMQ
- Routes measurements to appropriate applications
- Processes and sends commands to nodes
- Runs each application in its own thread

AicApp
~~~~~~

``AicApp`` is the base class for all control applications:

- Defines what measurements to subscribe to
- Specifies available control functions
- Implements ``process()`` for control logic
- Manages the command queue

@aic_app Decorator
~~~~~~~~~~~~~~~~~~

The decorator that registers applications:

- Registers the app with ``AicManager``
- Creates FastAPI REST endpoints
- Auto-generates MCP tools
- Auto-derives ``cell_ids`` from ``read_measurements`` and ``control_functions`` keys
- Initialises ``send_commands`` deque and ``agent_requests`` queue

AicManager
~~~~~~~~~~

The singleton manager that:

- Tracks all registered applications
- Stores FastAPI routers
- Provides access to the controller for state management
- Bridges the decorator, controller, and API layers

Registration Plane
------------------

.. code-block:: text

   ┌───────────────────────────────────────────────────────────────────────────────┐
   │                    REGISTRATION PLANE                                         │
   │                           │                                                   │
   │               ┌───────────▼───────────┐                                       │
   │               │     aic_register      │ ◄── Central registry                  │
   │               │     (Port 5558)       │     Stores node/app info in Redis     │
   │               │      REQ/REP          │     Returns broker connection info    │
   │               └───────────┬───────────┘                                       │
   │                           │                                                   │
   │                     ┌─────┴─────┐                                             │
   │                     │   Redis   │ ◄── Persistent state storage                │
   │                     │Port 6379  │                                             │
   │                     └───────────┘                                             │
   └───────────────────────────────────────────────────────────────────────────────┘

Registration Service
~~~~~~~~~~~~~~~~~~~~

The ``aic_register`` service:

- Receives registration requests via ZMQ REQ/REP
- Validates node and app registrations
- Stores state in Redis
- Returns broker connection information
- Monitors node health via heartbeats

Redis Storage
~~~~~~~~~~~~~

Redis stores:

- List of registered network nodes
- Available measurements per node
- Available control functions per node
- Registered AI applications
- Application configurations

Data Plane
----------

.. code-block:: text

   ┌───────────────────────────────────────────────────────────────────────────────┐
   │                         DATA PLANE (Message Broker)                           │
   │                                                                               │
   │                    ┌─────────────────────────────────────┐                    │
   │                    │         node_msg_broker             │                    │
   │                    │                                     │                    │
   │    Measurements:   │   PULL(5555) ──► PUB(5554)         │  ──► AIC Apps      │
   │    Nodes ─────────►│                                     │                    │
   │                    │   PULL(5556) ──► PUB(5557)         │  ──► Nodes         │
   │    Commands:       │                                     │                    │
   │    AIC Apps ──────►│                                     │                    │
   │                    └─────────────────────────────────────┘                    │
   │                                                                               │
   └───────────────────────────────────────────────────────────────────────────────┘

Message Broker
~~~~~~~~~~~~~~

The ``node_msg_broker`` runs two forwarding loops:

**Measurement Broker**:

- Nodes PUSH measurements to port 5555
- Broker publishes on port 5554
- Apps subscribe by topic (node_id)

**Command Broker**:

- Apps PUSH commands to port 5556
- Broker publishes on port 5557
- Nodes subscribe by topic (node_id)

Network Node Framework (controlled_entity)
-------------------------------------------

The ``controlled_entity`` package is the **node-side counterpart** to
``ai_nn_controller``. It provides an abstraction layer for building network
nodes that integrate with the ai_nn_controller system.

.. code-block:: text

   ┌───────────────────────────────────────────────────────────────────────────────┐
   │                            NETWORK NODES                                      │
   │                                                                               │
   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
   │   │  ControlledEntity│  │ ControlledEntity │  │ ControlledEntity│              │
   │   │   (Amp1Node)    │  │  (ROADM3Node)   │  │  (SrsranNode)  │   ...        │
   │   │                 │  │                  │  │                 │              │
   │   │ poll_measure-   │  │ poll_measure-    │  │ poll_measure-   │              │
   │   │  ments()        │  │  ments()         │  │  ments()        │              │
   │   │                 │  │ handle_command() │  │ setup()         │              │
   │   └───────┬─────────┘  └───────┬──────────┘  └───────┬─────────┘              │
   │           │                    │                      │                       │
   │           └────────────────────┴──────────────────────┘                       │
   │                                │                                              │
   │                      ┌─────────▼──────────┐                                   │
   │                      │     NodeRunner     │ ◄── Handles all ZMQ plumbing     │
   │                      │ (framework engine) │     Registration, heartbeats     │
   │                      └─────────┬──────────┘     Measurement PUSH, cmd SUB   │
   │                                │                                              │
   │                      PUSH measurements to broker (5555)                       │
   │                      SUB to commands from broker (5557)                       │
   │                                                                               │
   └───────────────────────────────────────────────────────────────────────────────┘

ControlledEntity
~~~~~~~~~~~~~~~~

The base class that all network nodes inherit from. It defines the southbound
interface:

- ``poll_measurements()`` — return current metrics as a dict
- ``handle_command(payload)`` — apply an incoming command (optional)
- ``setup()`` — one-time initialization after registration (optional)

@node Decorator
~~~~~~~~~~~~~~~

Registers a ``ControlledEntity`` subclass with the framework. Sets the node name,
validates that ``available_measurements`` is defined, and enforces one node per
process.

NodeRunner
~~~~~~~~~~

The execution engine that handles all northbound communication:

- ZMQ context and socket management
- Three-step registration with ``aic_register``
- Measurement publishing via PUSH socket
- Command ingestion via SUB socket
- Alive heartbeats on main thread
- Threading for concurrent operations

This separation means node developers only write southbound logic, while the
framework handles all framework-facing communication.

Communication Flows
-------------------

Registration Flow
~~~~~~~~~~~~~~~~~

.. code-block:: text

   1. Node/App connects to Register (port 5558) via REQ/REP
   2. Sends registration request with node_type and node_id
   3. Register validates and stores in Redis
   4. Register returns broker IP and port configuration
   5. Node/App connects to broker using received addresses

Measurement Flow
~~~~~~~~~~~~~~~~

.. code-block:: text

   Node (PUSH) → Broker:5555 (PULL) → Broker:5554 (PUB) → App (SUB)

   Wire format: "{node_id};{MessageEnvelope_JSON}"

   MessageEnvelope fields: schema, version, message_type, source, target,
                            correlation_id, lineage_id, idempotency_key, ts, payload

   Defined in: ai_nn_controller/protocol/envelope.py

Command Flow
~~~~~~~~~~~~

.. code-block:: text

   App (PUSH) → Broker:5556 (PULL) → Broker:5557 (PUB) → Node (SUB)

   Wire format: "{node_id};{MessageEnvelope_JSON}"

   The command parameters are carried in the envelope's ``payload`` field.

ZMQ Socket Types
----------------

.. list-table:: Socket Patterns
   :header-rows: 1
   :widths: 20 20 20 40

   * - Pattern
     - Sender
     - Receiver
     - Use Case
   * - REQ/REP
     - Nodes/Apps
     - Register
     - Registration handshake
   * - PUSH/PULL
     - Nodes
     - Broker
     - Measurement collection
   * - PUB/SUB
     - Broker
     - Apps
     - Measurement distribution
   * - PUSH/PULL
     - Apps
     - Broker
     - Command collection
   * - PUB/SUB
     - Broker
     - Nodes
     - Command distribution

Runtime Robustness
------------------

- **Graceful shutdown**: ``read_message()`` uses ``RCVTIMEO=1000 ms`` + ``zmq.Again`` so threads exit cleanly on stop
- **Bounded queues**: ``AIC_MAX_QUEUE_SIZE`` (controller side) and ``NODE_MAX_PENDING_COMMANDS`` (node side) prevent unbounded memory growth under load
- **Idempotency**: ``NodeRunner`` deduplicates incoming commands by ``idempotency_key`` using a FIFO LRU cache, so retried or duplicated commands are not applied twice

Key Design Principles
---------------------

1. **Dynamic Discovery**: Nodes and apps don't need hardcoded broker addresses
2. **Topic-Based Routing**: Messages are routed by node_id topic prefix
3. **Loose Coupling**: Components communicate through well-defined interfaces
4. **Scalability**: Multiple apps can run simultaneously, each in its own thread
5. **Persistent State**: Redis provides durable registration state
6. **AI-Ready**: MCP tools enable AI agent integration out of the box

Next Steps
----------

- :doc:`developing_apps` — Create your own control applications
- :doc:`developing_nodes` — Build network nodes with the controlled_entity framework
- :doc:`commands` — Define custom commands
- :doc:`../api/ai_nn_controller` — Core framework API reference
