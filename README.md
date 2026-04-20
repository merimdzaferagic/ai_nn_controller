# Dual Licensing
This project is offered under a choice of licences:
- AGPL (free, with copyleft obligations)
- Commercial licence (paid, no copyleft)

If you use this software in a closed-source or commercial product, you must obtain a commercial licence.

See LICENSE for AGPL.
See COMMERCIAL-LICENSE.md for terms summary.

# AI-Native Network Controller

**ai_nn_controller** is an open-source, AI-native network controller framework — the OpenClaw for networks — for building intelligent control applications that manage heterogeneous network equipment. It supports any type of network node — optical, wireless, RAN, core network, and beyond — through a unified control plane, a ZeroMQ-based message bus, and an automatic MCP (Model Context Protocol) layer that exposes every control capability to AI agents.


## Running the Examples

Two ready-to-run examples are included. Both only require Git, Docker, and Docker Compose.

### Step 1 — Install Docker and Docker Compose

**Ubuntu / Debian:**

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and back in after running `usermod`, then verify:

```bash
docker --version
docker compose version
```

**macOS / Windows:** install [Docker Desktop](https://www.docker.com/products/docker-desktop/), which includes Docker Compose.

---

### Step 2 — Clone this repository

```bash
git clone https://github.com/merimdzaferagic/ai_nn_controller.git
cd ai_nn_controller
```

---

### Example 1 — Optical Network Control Application

This example runs a simulated optical network: three amplifiers and three ROADMs generating live measurements, two control applications competing to send commands, and a conflict mitigator resolving them. Everything is exposed over REST and MCP on port 8000.

**Start the stack:**

```bash
docker compose -f docker-compose.yml up
```

Wait until you see the nodes registering and the controller printing measurements (about 25 seconds). Open a **second terminal** and start your AI agent.

**Install OpenCode** ([github.com/sst/opencode](https://github.com/sst/opencode)):

```bash
curl -fsSL https://opencode.ai/install | bash
```

**Start OpenCode pointing at the running MCP server:**

In the terminal, navigate to the `ai_nn_controller` directory and simply start `opencode`.

Once inside, try:

```
use the MCP and tell me how many applications are running
```

Then explore further:

```
read the latest measurements from all nodes
```

The agent will call the auto-generated MCP tools directly against the live running controller.

**Stop the stack:**

```bash
docker compose -f docker-compose.yml down
```

---

### Example 2 — srsRAN Read Measurements

This example connects to a live srsRAN gNodeB. It reads UE-level and system-level metrics from InfluxDB and exposes them via REST and MCP on port 8000.

**Start the srsRAN stack first.** Clone the srsRAN project and bring up its Docker Compose stack so that InfluxDB is running and the `docker_metrics` network exists:

```bash
git clone https://github.com/merimdzaferagic/CONVERGE-summer-school.git
cd CONVERGE-summer-school/srsRAN/docker
docker compose -f docker-compose_no_ric.yml up
```

Open a **new terminal**, go back to this repository (`ai_nn_controller`), and set your InfluxDB token in `network_nodes/srsran_node/node.conf`:

```ini
influxdb_token = <your-influxdb-token>
```

To identify the token for your setup run:

```ini
sudo docker exec influxdb env | grep -i token
```

**Start the ai_nn_controller srsRAN stack:**

```bash
cd ai_nn_controller
docker compose -f docker-compose.srsran.yml up
```

Wait until the srsRAN node connects and the reader starts printing measurements (about 25 seconds). Open a **second terminal** and start OpenCode:

Once inside, try:

```
use the MCP and tell me how many applications are running and start them all
```

Then explore the live RAN data:

```
read the latest measurements from the srsRAN node
```

```
what is the current CQI and uplink SNR?
```

```
get a full UE summary using the get_ue_summary tool
```

**Stop the stack:**

```bash
docker compose -f docker-compose.srsran.yml down
```

---

### Integrating a New Network Domain

Integrating any new type of network equipment — optical, wireless, RAN, core, or anything else — requires only two things:

1. **A network node adapter (examples in `network_nodes`)** — a Python class that inherits from `ControlledEntity` and implements `poll_measurements()` to read data from your equipment (via SNMP, gRPC, REST, InfluxDB, or any other interface). The `controlled_entity` package handles all registration and ZeroMQ plumbing automatically.

2. **A control application** — a Python class decorated with `@aic_app` that declares which measurements to subscribe to and which commands to send. The framework auto-generates the REST API and MCP tools from this declaration. Use `control_applications/control_application_v2_example/` as the starting template.

No changes to the controller, broker, or register are needed.

---

## Table of Contents

- [Running the Examples](#running-the-examples)
- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Developing Control Applications](#developing-control-applications)
- [Developing Network Nodes](#developing-network-nodes)
- [Template App Generator](#template-app-generator)
- [API Reference](#api-reference)
- [MCP Integration](#mcp-integration)
- [Communication Patterns](#communication-patterns)
- [Multi-Domain Network Integration](#multi-domain-network-integration)

---

## Overview

ai_nn_controller decouples application developers from infrastructure concerns. By annotating a Python class with a few decorators, a developer gets:

- **Declarative App Definition**: Define control apps with simple Python decorators
- **Automatic API Generation**: FastAPI REST endpoints auto-generated for each app
- **MCP Tool Generation**: AI agents (like Claude) can control apps via auto-generated MCP tools
- **Distributed Architecture**: Nodes, register, and message broker communicate via ZeroMQ
- **Dynamic Discovery**: Nodes and apps only need to know the register address; broker info is obtained at runtime

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONTROL PLANE                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     AIC Server (FastAPI)                             │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                      │   │
│  │  │NetworkApp1 │  │ NetworkApp2│  │ Conflict   │    ... more apps     │   │
│  │  │            │  │            │  │ Mitigator  │                      │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                      │   │
│  │        └───────────────┴───────────────┘                             │   │
│  │                        │                                             │   │
│  │              ┌─────────▼─────────┐                                   │   │
│  │              │   AicController   │ ◄── Manages app lifecycle         │   │
│  │              │ (ai_nn_controller │     Routes messages               │   │
│  │              │       pkg)        │     Sends commands                │   │
│  │              └─────────┬─────────┘                                   │   │
│  │                        │                                             │   │
│  │  REST API: /apps/*     │    MCP: /mcp/*                              │   │
│  └────────────────────────┼─────────────────────────────────────────────┘   │
│                           │                                                 │
│                     Port 8000                                               │
└───────────────────────────┼─────────────────────────────────────────────────┘
                            │
┌───────────────────────────┼───────────────────────────────────────────────────┐
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

┌───────────────────────────────────────────────────────────────────────────────┐
│                         DATA PLANE (Message Broker)                           │
│                                                                               │
│                    ┌─────────────────────────────────────┐                    │
│                    │         node_msg_broker             │                    │
│                    │                                     │                    │
│    Measurements:   │   PULL(5555) ──► PUB(5554)         │  ──► AIC Apps       │
│    Nodes ─────────►│                                     │                    │
│                    │   PULL(5556) ──► PUB(5557)         │  ──► Nodes          │
│    Commands:       │                                     │                    │
│    AIC Apps ──────►│                                     │                    │
│                    └─────────────────────────────────────┘                    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                            NETWORK NODES                                      │
│                                                                               │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐            │
│   │  Amp1   │  │  Amp2   │  │ ROADM1  │  │ ROADM2  │  │  srsRAN  │            │
│   │ (ID=3)  │  │ (ID=5)  │  │ (ID=4)  │  │ (ID=7)  │  │ (ID=10)  │  ...       │
│   │ Optical │  │ Optical │  │ Optical │  │ Optical │  │ Wireless │            │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬─────┘            │
│        │            │            │            │            │                   │
│        └────────────┴────────────┴────────────┴────────────┘                   │
│                                  │                                             │
│                      PUSH measurements to broker (5555)                        │
│                      SUB to commands from broker (5557)                        │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Registration Phase**:
   - Nodes and apps connect to `aic_register` (port 5558) via ZMQ REQ/REP
   - The register returns the broker IP and port configuration
   - All subsequent communication uses dynamically obtained addresses — nothing is hardcoded

2. **Measurement Flow** (Node → App):
   ```
   Node (PUSH) → Broker:5555 (PULL) → Broker:5554 (PUB) → App (SUB)
   Wire format: "{node_id};{MessageEnvelope_JSON}"
   ```

3. **Command Flow** (App → Node):
   ```
   App (PUSH) → Broker:5556 (PULL) → Broker:5557 (PUB) → Node (SUB)
   Wire format: "{node_id};{MessageEnvelope_JSON}"
   ```

### Port Summary

| Port | Service | Socket Type | Direction | Purpose |
|------|---------|-------------|-----------|---------|
| 5554 | Broker | PUB | → Apps | Measurement publication |
| 5555 | Broker | PULL | ← Nodes | Measurement collection |
| 5556 | Broker | PULL | ← Apps | Command collection |
| 5557 | Broker | PUB | → Nodes | Command publication |
| 5558 | Register | REP | ↔ All | Registration (REQ/REP) |
| 6379 | Redis | TCP | ↔ Register | State storage |
| 8000 | AIC Server | HTTP | ↔ Clients | REST API & MCP |

---

## Project Structure

```
.
├── control_applications/              # Control applications
│   └── control_application_v2_example/  # Reference app (optical network demo)
│       ├── aic_app.py               # App definitions (NetworkApp1, NetworkApp2, ConflictMitigator)
│       ├── aic_app.conf             # Registration config
│       ├── commands.py              # Command definitions (SET_GAIN, SET_VOA, etc.)
│       ├── pyproject.toml           # Package metadata
│       └── Dockerfile
│
├── network_nodes/                    # Network nodes (use controlled_entity)
│   ├── dummy_nodes/                 # Simulated nodes for testing
│   │   ├── amp1_node/              # Measurement-only amplifier
│   │   │   ├── node.py             # ControlledEntity subclass
│   │   │   ├── node.conf           # Node ID + register address
│   │   │   └── Dockerfile
│   │   ├── roadm3_with_command/     # ROADM with command handling
│   │   └── ...                      # amp2, amp3, roadm1, roadm2
│   │
│   ├── srsran_node/                 # srsRAN 5G RAN node (InfluxDB bridge)
│   │   ├── node.py                 # Polls InfluxDB via setup() hook
│   │   ├── node.conf               # InfluxDB connection + node config
│   │   └── Dockerfile
│   │
│   └── twilight_nodes/              # Twilight optical network bridge nodes
│       ├── twilight_client.py       # Shared REST client
│       └── ...                      # terminal, roadm, amp nodes
│
├── fastapi_client/                   # Python client for the AIC REST API
│   ├── client.py                    # Core API client
│   ├── cli.py                       # Interactive CLI
│   └── examples.py                  # Usage examples
│
├── controller_components/            # Core framework components
│   ├── ai_nn_controller/           # Control plane package (northbound)
│   │   ├── AicApp.py                # Base class for control apps
│   │   ├── AicController.py         # Runtime engine
│   │   ├── RegisterAicApp.py        # Registration with aic_register
│   │   ├── registry.py              # Command registry
│   │   ├── server.py                # FastAPI server creation
│   │   ├── decorators/
│   │   │   ├── aic_app.py          # @aic_app decorator
│   │   │   ├── command_validator.py # @command_validator decorator
│   │   │   └── agent_controlled.py # @agent_controlled decorator
│   │   ├── managers/
│   │   │   └── AicManager.py       # App lifecycle management
│   │   ├── mcp/                     # MCP integration
│   │   │   ├── server.py           # MCP JSON-RPC implementation
│   │   │   ├── tool_registry.py    # Tool storage
│   │   │   ├── tool_generator.py   # Auto-generates tools from apps
│   │   │   └── fastapi_integration.py
│   │   ├── protocol/
│   │   │   └── envelope.py         # MessageEnvelope (wire schema)
│   │   └── enums/
│   │       └── MeasurementsHandler.py
│   │
│   ├── controlled_entity/           # Node-side framework (southbound)
│   │   ├── ControlledEntity.py      # Base class for network nodes
│   │   ├── NodeRunner.py            # Node execution engine (ZMQ plumbing)
│   │   ├── decorators/
│   │   │   └── node.py             # @node decorator
│   │   └── parse_config.py          # node.conf parser
│   │
│   ├── register/                    # Central registry service
│   │   ├── register.py             # Main registration logic
│   │   ├── register.conf           # Configuration (broker IPs, ports)
│   │   └── register_utils/
│   │       └── RegisterInterface.py
│   │
│   └── node_msg_broker/             # ZMQ message broker
│       └── node_msg_broker.py      # PULL/PUB forwarding
│
└── docker-compose.yml               # Main orchestration file
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)

### Running with Docker Compose

```bash
# Clone the repository
git clone https://github.com/merimdzaferagic/ai_nn_controller.git
cd ai_nn_controller

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f aic_server

# Stop all services
docker-compose down
```

### Services Started

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| Redis | redis | 6379 | State storage |
| Register | aic_register | 5558 | Registration service |
| Broker | node_msg_broker | 5554-5557 | Message routing |
| AIC Server | aic_server | 8000 | FastAPI + MCP |
| Nodes | amp1_node, etc. | — | Simulated optical network nodes |

### Accessing the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **List Apps**: http://localhost:8000/apps

---

## Configuration

### Key Insight: Registration-Based Discovery

**Nodes and AIC apps only need to know the register's address.** The register returns the broker's address during the registration handshake. No other addresses need to be configured anywhere.

### Register Configuration (`register/register.conf`)

```ini
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
```

### AIC App Configuration (`aic_app.conf`)

```ini
ip_address = aic_register
register_port = 5558
```

### Node Configuration (`node.conf`)

```ini
ip_address = aic_register
register_port = 5558
node_id = 3
```

---

## Developing Control Applications

### Step 1: Create the App File

```python
from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.AicApp import AicApp

import commands  # Register domain commands before @aic_app executes

@aic_app(name="MyControlApp")
class MyControlApp(AicApp):
    """My custom network control application."""

    aic_app_id = 100
    control_loop_update_time = 2

    # Measurements to read (dict: node_id → list of metric names)
    read_measurements = {
        3: ["amp1_target_gain", "amp1_gain_tilt"],
        8: ["roadm3_preamp_target_gain"],
    }

    # Control functions available (dict: node_id → list of command names)
    control_functions = {
        8: ["SET_GAIN", "SET_VOA"]
    }

    # cell_ids and send_commands are auto-generated by @aic_app
    # cell_ids will be: [3, 8]

    @classmethod
    def process(cls, measurements):
        """Called periodically with latest measurements."""
        amp1_data = measurements.get(3, [{}])[-1] if measurements.get(3) else {}
        current_gain = amp1_data.get("amp1_target_gain", 0)

        if current_gain > 25:
            cls.add_command((
                "SET_GAIN",
                {"node_id": 8, "value": {"amp_type": "preamp", "target_gain": 20.0}}
            ))
```

### Step 2: Define Commands

```python
import json
from ai_nn_controller.registry import register_command

def set_gain_handler(node_id: int, value: dict) -> str:
    return json.dumps({
        "amp_type": value.get("amp_type", "line"),
        "target_gain": value.get("target_gain", 0)
    })

SET_GAIN_SCHEMA = {
    "description": "Set the target gain for an amplifier",
    "properties": {
        "node_id": {"type": "integer", "description": "Target node ID"},
        "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
        "target_gain": {"type": "number", "description": "Target gain in dB"}
    },
    "required": ["node_id", "target_gain"]
}

register_command(name="SET_GAIN", handler=set_gain_handler, schema=SET_GAIN_SCHEMA)
```

### Step 3: Add Command Validators (Optional)

Command validators provide guardrails for commands sent via the REST API or MCP tools. They run before any command is dispatched to a node.

```python
from ai_nn_controller.decorators.command_validator import command_validator

@aic_app(name="MyControlApp")
class MyControlApp(AicApp):
    control_functions = {8: ["SET_GAIN"]}
    MAX_GAIN = 25.0

    # IMPORTANT: @classmethod must be ABOVE @command_validator
    @classmethod
    @command_validator("SET_GAIN")
    def validate_set_gain(cls, params: dict) -> tuple[bool, str | None]:
        target_gain = params.get("target_gain", 0)
        if target_gain > cls.MAX_GAIN:
            return False, f"Gain {target_gain} exceeds max {cls.MAX_GAIN} dB"
        if target_gain < 0:
            return False, "Gain cannot be negative"
        return True, None
```

### Step 4: Add Agent-Controlled Operations (Optional)

Agent-controlled operations let an MCP/AI agent execute logic **inside the process loop**, with access to live measurements and app-internal state.

```python
from ai_nn_controller.decorators.agent_controlled import agent_controlled

@aic_app(name="SmartApp")
class SmartApp(AicApp):
    read_measurements = {8: ["preamp_gain"]}
    control_functions = {8: ["SET_GAIN"]}
    MAX_GAIN = 25.0

    # IMPORTANT: @classmethod must be ABOVE @agent_controlled
    @classmethod
    @agent_controlled(
        name="optimize_gain",
        description="Optimize gain based on a strategy",
        schema={
            "properties": {
                "node_id": {"type": "integer"},
                "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
            },
            "required": ["node_id", "strategy"]
        }
    )
    def handle_optimize_gain(cls, request, measurements):
        """Runs inside the process loop with access to live measurements."""
        node_id = request["node_id"]
        latest = measurements.get(node_id, [{}])[-1] or {}
        current_gain = latest.get("preamp_gain", 15.0)
        new_gain = min(current_gain + 2.0, cls.MAX_GAIN) if request["strategy"] == "max_snr" \
                   else max(current_gain - 2.0, 0.0)

        cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"target_gain": new_gain}}))
        return {"status": "applied", "previous_gain": current_gain, "new_gain": new_gain}

    @classmethod
    def process(cls, measurements):
        pass
```

**How it works:**

1. Agent calls the MCP tool `SmartApp_optimize_gain`
2. An `AgentRequest` is pushed to the app's internal queue
3. On the next `process()` cycle, the controller calls the handler with live measurements
4. The handler queues commands and returns a result dict to the MCP caller

### Step 5: Create Configuration Files

**`aic_app.conf`**:
```ini
ip_address = aic_register
register_port = 5558
```

### Step 6: Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install /ai_nn_controller

COPY control_applications/my_app/ /app/

CMD ["python", "aic_app.py", "--verbose"]
```

### Step 7: Add to docker-compose.yml

```yaml
my_control_app:
  container_name: my_control_app
  build:
    context: ./
    dockerfile: control_applications/my_app/Dockerfile
  volumes:
    - ./control_applications/my_app/:/app
    - ./controller_components/ai_nn_controller/:/ai_nn_controller
  ports:
    - "8001:8000"
  networks:
    - aic_network
  depends_on:
    - aic_register
    - node_msg_broker
```

### Auto-Generated Endpoints

The `@aic_app` decorator automatically creates:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/apps/MyControlApp/info` | GET | App configuration |
| `/apps/MyControlApp/state` | GET | Current state |
| `/apps/MyControlApp/state` | PUT | Update state |
| `/apps/MyControlApp/measurements` | GET | Latest measurements |
| `/apps/MyControlApp/control` | POST | Send manual command |

### Auto-Generated MCP Tools

For each app, these MCP tools are created:

| Tool Name | Type | Description |
|-----------|------|-------------|
| `MyControlApp_set_gain` | control | Execute SET_GAIN command |
| `MyControlApp_get_measurements` | measurement | Get current measurements |
| `MyControlApp_get_state` | state | Get app state |
| `MyControlApp_set_state` | state | Set app state |
| `MyControlApp_optimize_gain` | agent_controlled | Run inside process loop (if `@agent_controlled` defined) |

---

## Developing Network Nodes

Network nodes are built using the `controlled_entity` package — the node-side counterpart to `ai_nn_controller`. It provides a base class (`ControlledEntity`) that abstracts away all northbound ZMQ plumbing (registration, measurement publishing, command ingestion, heartbeats). Node developers only implement the **southbound interface**: how to get measurements and how to apply commands.

### The `controlled_entity` Package

```python
from controlled_entity import ControlledEntity, node, NodeRunner
```

| Component | Role |
|-----------|------|
| `ControlledEntity` | Base class — subclass this for your node |
| `@node(name="...")` | Decorator that registers the node class |
| `NodeRunner` | Engine that handles all ZMQ communication |

### Step 1: Define a Measurement-Only Node

```python
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
```

### Step 2: Add Command Handling (Optional)

```python
@node(name="ROADM3")
class ROADM3Node(ControlledEntity):
    available_measurements = ["session_id", "roadm3_preamp_target_gain", "roadm3_booster_target_gain"]
    available_controls = ["SET_GAIN", "SET_VOA", "SET_TILT"]
    measurement_interval = 5.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "roadm3_preamp_target_gain": round(random.uniform(17.0, 21.0), 2),
            "roadm3_booster_target_gain": round(random.uniform(14.0, 19.0), 2),
        }

    def handle_command(self, payload):
        if "target_gain" in payload:
            print(f"[ROADM3] Setting target gain to: {payload['target_gain']}")
        return True
```

### Step 3: Use the `setup()` Hook for External Data Sources

For real-world nodes that connect to external systems (databases, REST APIs, hardware), use `setup()`. It runs once after registration completes.

```python
@node(name="srsRAN")
class SrsranNode(ControlledEntity):
    available_measurements = ["dl_bitrate", "ul_bitrate", "cqi", "cpu_usage_percent"]
    measurement_interval = 1.0

    def setup(self):
        self._latest_metrics = {}
        self._metrics_lock = threading.Lock()
        thread = threading.Thread(target=self._poll_influxdb, daemon=True)
        thread.start()

    def _poll_influxdb(self):
        # Query InfluxDB, update self._latest_metrics
        ...

    def poll_measurements(self):
        with self._metrics_lock:
            current = dict(self._latest_metrics)
        return current if current else None
```

### Step 4: Create `node.conf`

```ini
ip_address = aic_register
register_port = 5558
node_id = 3
```

### How It Works Under the Hood

When `NodeRunner().run()` is called, the framework handles everything:

```
NodeRunner().run()
 ├── Register with aic_register (REQ/REP)
 ├── Connect to broker (PUSH for measurements, SUB for commands)
 ├── Call node.setup()
 ├── Start measurement thread → poll_measurements() → PUSH to broker
 ├── Start command thread → SUB from broker → handle_command()
 └── Main thread → alive heartbeats
```

### Key Design Principle

- **Southbound** (you implement): `poll_measurements()`, `handle_command()`, `setup()`
- **Northbound** (framework handles): ZMQ registration, socket management, message serialization, heartbeats, threading

See `network_nodes/dummy_nodes/` for complete working examples.

---

## Template App Generator

Generate a full template control app based on whatever nodes have already registered.

**Important:** Run this *after* starting the stack, so nodes have time to register.

```bash
docker compose up -d
docker exec -it aic_register python3 /register/generate_template_app.py
```

Optional flags:

```bash
docker exec -it aic_register python3 /register/generate_template_app.py \
  --app-name template_app \
  --app-id 100 \
  --update-time 2 \
  --output-root /control_applications \
  --compose-output /workspace/docker-compose-test.yml
```

This creates `control_applications/template_app/` with:
- `Dockerfile`
- `aic_app.conf`
- `aic_app.py`
- `commands.py`
- `requirements.txt`

It also writes `docker-compose-test.yml` containing only the currently registered nodes plus the generated app.

---

## API Reference

### List All Apps

```bash
curl http://localhost:8000/apps
```

### Start an App

```bash
curl -X PUT http://localhost:8000/apps/NetworkApp1/state \
  -H "Content-Type: application/json" \
  -d '{"state": "running"}'
```

### Get Measurements

```bash
curl http://localhost:8000/apps/NetworkApp1/measurements
```

### Send Manual Command

```bash
curl -X POST http://localhost:8000/apps/NetworkApp1/control \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": 8,
    "command": "SET_GAIN",
    "payload": {"amp_type": "preamp", "target_gain": 15.0}
  }'
```

---

## MCP Integration

ai_nn_controller automatically exposes all control capabilities to AI agents via the Model Context Protocol (MCP).

### MCP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/` | GET | MCP server info |
| `/mcp/tools` | GET | List all MCP tools |
| `/mcp/tools/{app_name}` | GET | Tools for specific app |
| `/mcp/tools/call` | POST | Execute an MCP tool |
| `/mcp/message` | POST | Raw MCP JSON-RPC 2.0 |
| `/mcp/sse` | GET | Server-Sent Events stream |

### Call MCP Tool

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetworkApp1_set_state",
    "arguments": {"state": "running"}
  }'
```

### Call Agent-Controlled Tool

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetworkApp1_optimize_gain",
    "arguments": {"node_id": 8, "strategy": "max_snr"}
  }'
```

Response:
```json
{
  "success": true,
  "result": {
    "result": {"status": "applied", "previous_gain": 15.0, "new_gain": 17.0},
    "request_id": "abc-123-def"
  }
}
```

**Note:** The app must be in `running` state for agent-controlled tools to work.

---

## Communication Patterns

### ZMQ Socket Types

| Pattern | Sender | Receiver | Use Case |
|---------|--------|----------|----------|
| REQ/REP | Nodes/Apps | Register | Registration handshake |
| PUSH/PULL | Nodes | Broker | Measurement collection |
| PUB/SUB | Broker | Apps | Measurement distribution |
| PUSH/PULL | Apps | Broker | Command collection |
| PUB/SUB | Broker | Nodes | Command distribution |

### Message Format

All data messages use the versioned envelope format:
```
"{topic};{MessageEnvelope_JSON}"
```

Where:
- `topic` = node_id (string) — used by ZMQ PUB/SUB for routing
- `MessageEnvelope_JSON` = JSON-serialised `MessageEnvelope` object (schema: `urn:ai-nnc:envelope:1`)

`MessageEnvelope` fields: `schema`, `version`, `message_type`, `source`, `target`, `correlation_id`, `lineage_id`, `idempotency_key`, `ts`, `payload`.

`MessageEnvelope` is defined in `controller_components/ai_nn_controller/protocol/envelope.py` and is the authoritative wire schema.

### Registration Protocol

**Node Registration:**
```
1. Node → Register: {"node_type": "network_node", "node_id": 3, "msg_type": "register"}
2. Register → Node: {"msg_type": "ack", ...}
3. Node → Register: {"msg_type": "pm_availability", "available_pms": [...]}
4. Register → Node: {"msg_type": "ack", "databus_ip": "node_msg_broker",
                      "send_pm_port": "5555", "recv_command_port": "5557"}
```

**App Registration:**
```
1. App → Register: {"node_type": "aic_app", "node_id": -1, "msg_type": "register"}
2. Register → App: {"msg_type": "ack", "network_node_list": [...], ...}
3. App → Register: {"msg_type": "pm_ctrl_req", "list_of_pm": {...}, "list_of_ctrl": {...}}
4. Register → App: {"msg_type": "ack", "databus_ip": "node_msg_broker",
                     "ai_app_listen_port": "5554", "ai_app_send_command_port": "5556"}
```

---

## Multi-Domain Network Integration

ai_nn_controller is **domain-agnostic** — the same controller, message bus, and agentic layer work across heterogeneous network domains.

| Domain | Node Examples | Metrics / Controls |
|--------|--------------|-------------------|
| **Optical** | Amplifiers (EDFA), ROADMs | Gain, tilt, VOA attenuation, channel allocation |
| **Wireless (RAN)** | srsRAN gNodeB (via InfluxDB) | DL/UL bitrate, BLER, MCS, CQI, SNR, BSR |
| **Core Network** | *(pluggable)* | Session counts, latency, throughput |

Each domain is integrated by subclassing `ControlledEntity` and implementing `poll_measurements()`. The node can source data from any backend:

- **Simulated data** (built-in dummy nodes — see `network_nodes/dummy_nodes/`)
- **REST APIs** (Twilight optical nodes)
- **InfluxDB / time-series DBs** (srsRAN node polls InfluxDB via `setup()` hook)
- **gRPC, SNMP, NETCONF**, or any other telemetry source

Once a node registers and pushes measurements, every control application and AI agent can consume them regardless of the underlying domain.

See `docs/examples/srsran_integration.rst` for a complete multi-domain integration walkthrough.

---

## Troubleshooting

### App Not Receiving Measurements

1. Check app is in `running` state: `GET /apps/{name}/state`
2. Verify `read_measurements` includes the node IDs you want to subscribe to
3. Check broker logs: `docker-compose logs node_msg_broker`

### Commands Not Reaching Nodes

1. Ensure the command is registered in `commands.py`
2. Verify the node has `available_controls` set and is subscribed to commands
3. Check broker command forwarding: `docker-compose logs node_msg_broker`

### MCP Tools Not Generated

1. Ensure `control_functions` and `read_measurements` are dicts (not lists)
2. Check for import errors in the command registry
3. Verify `@aic_app(name="...")` is applied to the class

---

## Licensing
This project is dual-licensed under:

1. GNU Affero General Public License v3 (see LICENSE) – free for open-source and compliant use.
2. Commercial licence – for proprietary, embedded, or closed-source use.


## Contributing

Contributions are welcome. See `docs/contributing/` for guidelines.
