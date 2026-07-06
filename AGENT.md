# AGENT.md — AI-Native Network Controller: Developer Guide

This file is the authoritative briefing for AI coding agents working in this repository.
Read it completely before generating any code. Following the rules here keeps developer
work isolated to the correct folders and prevents accidental breakage of the shared
controller infrastructure.

---

## What This Repository Does

`ai_nn_controller` is a framework for building intelligent, AI-native control applications
over heterogeneous network equipment (optical, wireless, RAN, core, or anything else).
Three types of extension points exist:

| What you want to build | Where to work |
|---|---|
| **Control application** — logic that reads measurements and sends commands | `control_applications/<your_app>/` |
| **Plugin** — reusable service adapter (InfluxDB, MLflow, Prometheus, …) | `plugins/<your_plugin>/` |
| **Network node** — adapter that connects real or simulated equipment | `network_nodes/<domain>/<your_node>/` |

**Never touch `controller_components/`.** That directory contains the core framework
packages (`ai_nn_controller`, `controlled_entity`, `register`, `node_msg_broker`). They
are consumed as installed Python packages; they are not edited by application or node
developers.

---

## Repository Layout

```
.
├── control_applications/          ← Your control apps go here
│   └── control_application_v2_example/   ← Reference implementation; copy this
│       ├── aic_app.py             ← App class definitions + AicController entrypoint
│       ├── commands.py            ← Domain command handlers + JSON schemas
│       ├── aic_app.conf           ← Register address (aic_register:5558)
│       ├── pyproject.toml         ← Package metadata + entry-point declaration
│       ├── requirements.txt       ← Extra pip deps (if any)
│       ├── Dockerfile             ← Multi-stage build (framework → plugins → app)
│       ├── docker-compose.yml     ← Standalone compose for this app only
│       └── README.md
│
├── plugins/                       ← Your plugins go here
│   └── console_plugin/            ← Reference plugin; copy this
│       ├── aic_plugin.py          ← Plugin class definition
│       ├── pyproject.toml         ← Package metadata + ai_nn_controller.plugin_init EP
│       ├── Dockerfile             ← Required — plugin is installed from this image
│       └── README.md
│                                  (no docker-compose.yml — plugin is a package, not a service)
│
├── network_nodes/                 ← Your network nodes go here
│   ├── dummy_nodes/               ← Simulated nodes (use as templates)
│   │   ├── amp1_node/             ← Measurement-only node
│   │   └── roadm3_with_command/   ← Node with command handling
│   ├── srsran_node/               ← Real-world node (InfluxDB bridge)
│   └── twilight_nodes/            ← Real-world optical nodes (REST bridge)
│       └── <node>/
│           ├── node.py            ← ControlledEntity subclass
│           ├── node.conf          ← node_id + register address
│           └── Dockerfile         ← Required — node service is added to the root docker-compose.yml
│
├── controller_components/         ← DO NOT EDIT — shared framework
│   ├── ai_nn_controller/          ← Control-plane Python package
│   ├── controlled_entity/         ← Node-side Python package
│   ├── register/                  ← Central registry service
│   └── node_msg_broker/           ← ZMQ message broker
│
├── docker-compose.yml             ← Full-stack compose (all nodes + infra + example app)
├── docker-compose.srsran.yml      ← srsRAN-specific stack
└── fastapi_client/                ← Python REST client + CLI for manual testing
```

---

## Architecture in One Picture

```
AI Agent / Human
       │  REST (port 8000) + MCP (port 8000/mcp)
       ▼
┌─────────────────────────────────────┐
│  AIC Server (FastAPI)               │  ← your aic_app.py starts this via
│  ┌──────────┐  ┌──────────┐         │    AicController(with_api=True).run()
│  │  App 1   │  │  App 2   │  ...    │
│  └────┬─────┘  └────┬─────┘         │
│       └──────┬───────┘               │
│       AicController                  │
└──────────────┼──────────────────────┘
               │ ZeroMQ (via broker)
┌──────────────┼──────────────────────┐
│  node_msg_broker                     │
│  PULL:5555 → PUB:5554  (measurements)│
│  PULL:5556 → PUB:5557  (commands)    │
└──────────────┼──────────────────────┘
               │
┌──────────────┼──────────────────────┐
│  aic_register (port 5558)            │
│  Redis (port 6379)                   │
└──────────────┼──────────────────────┘
               │
   Network nodes (each in its own container)
   PUSH measurements → broker:5555
   SUB commands ← broker:5557
```

Nodes and apps only need to know `aic_register:5558`. The register hands back the
broker address at registration time — nothing else is hardcoded.

### Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 5554 | broker PUB | Measurements → apps |
| 5555 | broker PULL | Measurements ← nodes |
| 5556 | broker PULL | Commands ← apps |
| 5557 | broker PUB | Commands → nodes |
| 5558 | register REP | Registration (all) |
| 6379 | Redis | Register state |
| 8000 | AIC Server | REST API + MCP |

---

## Building a Control Application

A control application reads measurements from one or more network nodes and (optionally)
sends commands back to them. The framework auto-generates REST endpoints and MCP tools
from the app's declaration — no FastAPI code is needed.

### Step 1 — Create the directory

```
control_applications/
└── my_app/
    ├── aic_app.py
    ├── commands.py
    ├── aic_app.conf
    ├── pyproject.toml
    ├── requirements.txt      ← optional
    ├── Dockerfile
    └── docker-compose.yml    ← required so the app can be run standalone
```

### Step 2 — `aic_app.conf`

Always identical across apps — only the register address matters:

```ini
ip_address = aic_register
register_port = 5558
```

### Step 3 — `commands.py`

Define every command the app may issue. Import `register_command` from the framework
(never from `controller_components` directly).

```python
import json
from ai_nn_controller.registry import register_command

def set_gain_handler(node_id: int, value: dict) -> str:
    return json.dumps({"target_gain": value.get("target_gain")})

SET_GAIN_SCHEMA = {
    "description": "Set amplifier target gain",
    "properties": {
        "node_id":      {"type": "integer"},
        "target_gain":  {"type": "number", "description": "dB"}
    },
    "required": ["node_id", "target_gain"]
}

register_command(name="SET_GAIN", handler=set_gain_handler, schema=SET_GAIN_SCHEMA)
```

**Rules:**
- The handler receives `(node_id: int, value: dict)` and must return a JSON string.
- The schema is used for MCP tool generation — describe parameters clearly.
- `commands.py` is imported at module load time (before `@aic_app` executes), so
  commands are registered before the decorator runs.

### Step 4 — `aic_app.py`

```python
from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.AicApp import AicApp
from ai_nn_controller.AicController import AicController
import commands  # registers commands — must be imported before @aic_app
import argparse

@aic_app(name="MyApp")
class MyApp(AicApp):
    aic_app_id = 100              # unique integer across all apps in the stack
    control_loop_update_time = 2  # seconds between process() calls

    # node_id → list of metric names to subscribe to
    read_measurements = {
        3: ["amp1_target_gain", "amp1_gain_tilt"],
    }

    # node_id → list of command names this app may send
    control_functions = {
        3: ["SET_GAIN"]
    }

    @classmethod
    def process(cls, measurements):
        latest = (measurements.get(3) or [{}])[-1]
        gain = latest.get("amp1_target_gain", 0)
        if gain > 22:
            cls.add_command(("SET_GAIN", {"node_id": 3, "value": {"target_gain": 18.0}}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    AicController(with_api=True, api_host=args.host, api_port=args.port, verbose=args.verbose).run()
```

**Key rules:**
- `aic_app_id` must be unique across every app in the same running stack.
- `read_measurements` and `control_functions` must be dicts, not lists.
- `process(cls, measurements)` is a `@classmethod`. `measurements` is
  `{node_id: [dict, ...]}` — a list of snapshots per node, most recent last.
- Call `cls.add_command(("COMMAND_NAME", {"node_id": X, "value": {...}}))` to queue a
  command. The controller dispatches it to the node after `process()` returns.
- Multiple apps in one file is fine — the `control_application_v2_example` shows three.

### Step 5 — Optional decorators

#### `@command_validator` — validate before dispatch

```python
from ai_nn_controller.decorators.command_validator import command_validator

@aic_app(name="MyApp")
class MyApp(AicApp):
    @classmethod                        # @classmethod MUST be above @command_validator
    @command_validator("SET_GAIN")
    def validate_set_gain(cls, params: dict) -> tuple[bool, str | None]:
        if params.get("target_gain", 0) > 25:
            return False, "gain exceeds 25 dB"
        return True, None
```

#### `@agent_controlled` — AI-callable operation inside the process loop

```python
from ai_nn_controller.decorators.agent_controlled import agent_controlled

@aic_app(name="MyApp")
class MyApp(AicApp):
    @classmethod                        # @classmethod MUST be above @agent_controlled
    @agent_controlled(
        name="optimize_gain",
        description="Optimize gain based on strategy",
        schema={
            "properties": {
                "node_id": {"type": "integer"},
                "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
            },
            "required": ["node_id", "strategy"]
        }
    )
    def handle_optimize_gain(cls, request, measurements):
        node_id = request["node_id"]
        latest = (measurements.get(node_id) or [{}])[-1]
        current = latest.get("amp1_target_gain", 15.0)
        new_gain = min(current + 2, 25) if request["strategy"] == "max_snr" else max(current - 2, 0)
        cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"target_gain": new_gain}}))
        return {"previous": current, "new": new_gain}
```

The handler runs inside the next `process()` cycle with live measurements. An MCP tool
named `MyApp_optimize_gain` is auto-generated.

#### Plugins — optional service dependencies

```python
@aic_app(name="MyApp")
class MyApp(AicApp):
    required_plugins = ["ConsolePlugin"]   # controller refuses to start if missing

    @classmethod
    def process(cls, measurements):
        cls.plugins["ConsolePlugin"].log("tick")
```

### Step 6 — `pyproject.toml`

Required so the app's entry-point is discovered (registers commands automatically):

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["ai_nn_controller>=1.0.0"]

[project.entry-points."ai_nn_controller.app_init"]
"my_app:aic_app:commands" = "ai_nn_controller.plugins.entrypoints:bootstrap_application_bundle"

[tool.setuptools]
py-modules = ["aic_app", "commands"]
```

### Step 7 — `Dockerfile`

Install order is always: **framework → plugins → app**. The build context must be the
repository root so `controller_components/` is available.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y net-tools procps curl

# 1. Framework
COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install /ai_nn_controller

# 2. Plugins (add one COPY+RUN block per plugin)
COPY plugins/console_plugin/ /console_plugin/
RUN pip install --no-cache-dir /console_plugin

# 3. App dependencies
COPY control_applications/my_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. App package (registers entry-point)
COPY control_applications/my_app/pyproject.toml /app_pkg/
COPY control_applications/my_app/aic_app.py    /app_pkg/
COPY control_applications/my_app/commands.py   /app_pkg/
RUN pip install --no-cache-dir /app_pkg

# 5. Runtime copies for docker-compose volume-mount dev workflow
COPY control_applications/my_app/aic_app.py  .
COPY control_applications/my_app/aic_app.conf .
COPY control_applications/my_app/commands.py  .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python3", "aic_app.py", "--verbose"]
```

### Step 8 — `docker-compose.yml` (app-local, **required**)

Every control application must ship its own `docker-compose.yml` so it can be run
standalone (against an already-running infra stack) or integrated into the root compose.

```yaml
# control_applications/my_app/docker-compose.yml
# Run standalone: docker compose -f docker-compose.yml -f control_applications/my_app/docker-compose.yml up
# Requires the shared aic_network to already exist (created by the root compose).

services:
  my_app:
    container_name: my_app
    build:
      context: ../../          # repository root — needed for controller_components/
      dockerfile: control_applications/my_app/Dockerfile
    volumes:
      - ./:/app
      - ../../controller_components/ai_nn_controller/:/ai_nn_controller
      - ../../plugins/console_plugin/:/console_plugin
    ports:
      - "8000:8000"
    networks:
      - aic_network
    depends_on:
      - aic_register
      - node_msg_broker
    environment:
      - PYTHONUNBUFFERED=1
    command: >
      sh -c "sleep 25
      && pip install --no-cache-dir /ai_nn_controller
      && pip install --no-cache-dir /console_plugin
      && pip install --no-cache-dir /app
      && python3 aic_app.py --verbose"

networks:
  aic_network:
    external: true
```

To wire the app into the root `docker-compose.yml`, add its service block under
`services:` in that file, pointing `dockerfile:` at
`control_applications/my_app/Dockerfile`. See `aic_server` in the root compose for the
exact pattern.

---

## Building a Plugin

Plugins are reusable Python packages that extend control apps with external service
integrations (databases, model registries, monitoring, etc.). They are loaded via
Python entry points at controller startup.

### Step 1 — Create the directory

```
plugins/
└── my_plugin/
    ├── aic_plugin.py
    ├── pyproject.toml
    ├── Dockerfile             ← required
    └── README.md
```

Plugins are Python packages installed **inside** the app container — they do not run as
separate services and do not need their own `docker-compose.yml`.

### Step 2 — `aic_plugin.py`

```python
from ai_nn_controller.plugin_framework import AicPlugin, aic_plugin

@aic_plugin(name="MyPlugin", plugin_type="generic")
class MyPlugin(AicPlugin):

    @classmethod
    def connect(cls) -> None:
        # Called at controller startup — open connections here
        pass

    @classmethod
    def disconnect(cls) -> None:
        # Called at controller shutdown — release resources here
        pass

    @classmethod
    def is_healthy(cls) -> bool:
        return True

    # Add your public API methods here:
    @classmethod
    def do_something(cls, data: dict) -> None:
        pass
```

Available base classes (pick one to inherit from instead of `AicPlugin` for typed APIs):

| Base class | `plugin_type` | Implement |
|---|---|---|
| `AicPlugin` | `"generic"` | `connect`, `disconnect`, `is_healthy` |
| `StoragePlugin` | `"storage"` | + `write(key, value, tags)`, `read(query)` |
| `ModelRegistryPlugin` | `"model_registry"` | + `load_model(name, version)`, `save_model(name, model, metrics)` |
| `MonitoringPlugin` | `"monitoring"` | + `push_metric(name, value, labels)`, `get_metric(name, labels)` |

### Step 3 — `pyproject.toml`

The entry-point group `ai_nn_controller.plugin_init` is what makes the plugin
auto-discoverable. The entry-point name format is `bundle_name:module_name`.

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-plugin"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["ai_nn_controller>=1.0.0"]

[project.entry-points."ai_nn_controller.plugin_init"]
"my_plugin:aic_plugin" = "ai_nn_controller.plugin_framework.entrypoints:bootstrap_plugin_bundle"

[tool.setuptools]
py-modules = ["aic_plugin"]
```

### Step 4 — `Dockerfile`

Every plugin ships a `Dockerfile`. The build context is the repository root so
`controller_components/` is reachable.

```dockerfile
FROM python:3.11-slim

COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install /ai_nn_controller

COPY plugins/my_plugin/ /my_plugin/
RUN pip install /my_plugin
```

### Step 5 — Add to the app's Dockerfile and root docker-compose

Plugins are installed **inside** the app container — they do not get their own
`docker-compose.yml`. Wire them in two places:

**In the control app's `Dockerfile`** (after framework, before app):

```dockerfile
COPY plugins/my_plugin/ /my_plugin/
RUN pip install --no-cache-dir /my_plugin
```

**In the root `docker-compose.yml`** (under the `aic_server` service), add a volume
mount and include the install in the startup command:

```yaml
aic_server:
  volumes:
    - ./plugins/my_plugin/:/my_plugin
  command: >
    sh -c "sleep 25
    && pip install --no-cache-dir /ai_nn_controller
    && pip install --no-cache-dir /my_plugin
    && pip install --no-cache-dir /app
    && python3 aic_app.py --verbose"
```

### Step 6 — Declare the plugin in the control app

```python
@aic_app(name="MyApp")
class MyApp(AicApp):
    required_plugins = ["MyPlugin"]   # controller aborts at startup if not installed

    @classmethod
    def process(cls, measurements):
        plugin = cls.plugins["MyPlugin"]
        plugin.do_something({"key": "value"})
```

---

## Integrating a Network Node

A network node is a Python process that connects to real or simulated equipment,
periodically polls measurements, and optionally handles commands. It uses the
`controlled_entity` package, which handles all ZMQ plumbing automatically.

### Step 1 — Create the directory

```
network_nodes/
└── my_domain/
    └── my_node/
        ├── node.py
        ├── node.conf
        ├── Dockerfile             ← required
        └── docker-compose.yml     ← required
```

### Step 2 — `node.conf`

```ini
ip_address   = aic_register
register_port = 5558
node_id      = 20          # must be a unique integer in the running stack
pub_port     = 5590        # local outbound port (pick one not already in use)
```

Additional keys (e.g. `influxdb_token`) are available as `self.config["key"]` inside the
node class.

### Step 3 — `node.py`

**Measurement-only node:**

```python
from controlled_entity import ControlledEntity, node, NodeRunner
import time

@node(name="MyNode")
class MyNode(ControlledEntity):
    available_measurements = ["metric_a", "metric_b"]
    measurement_interval = 1.0          # seconds

    def poll_measurements(self):
        # Return a dict mapping metric name → value, or None to skip this cycle
        return {"metric_a": 42.0, "metric_b": 7.3}

if __name__ == "__main__":
    NodeRunner().run()
```

**Node that also receives commands:**

```python
@node(name="MyNode")
class MyNode(ControlledEntity):
    available_measurements = ["metric_a"]
    available_controls     = ["SET_PARAM"]   # command names this node handles
    measurement_interval   = 2.0

    def poll_measurements(self):
        return {"metric_a": self._current_value}

    def handle_command(self, payload: dict) -> bool:
        # payload is the JSON-decoded dict from the command handler in commands.py
        if "param_value" in payload:
            self._current_value = payload["param_value"]
        return True
```

**Node with external data source (`setup()` hook):**

```python
import threading

@node(name="MyNode")
class MyNode(ControlledEntity):
    available_measurements = ["metric_a"]
    measurement_interval = 1.0

    def setup(self):
        # Called once after registration — start background threads here
        self._latest = {}
        self._lock = threading.Lock()
        t = threading.Thread(target=self._poll_external, daemon=True)
        t.start()

    def _poll_external(self):
        while True:
            data = fetch_from_hardware()   # your real implementation
            with self._lock:
                self._latest = data
            time.sleep(1)

    def poll_measurements(self):
        with self._lock:
            return dict(self._latest) or None
```

**Framework lifecycle (handled automatically — do not replicate):**

```
NodeRunner().run()
 ├── Register with aic_register (REQ/REP on port 5558)
 ├── Obtain broker address from register response
 ├── Connect ZMQ sockets (PUSH measurements, SUB commands)
 ├── Call node.setup()
 ├── Start measurement thread → poll_measurements() → PUSH to broker every interval
 ├── Start command thread → SUB from broker → handle_command()
 └── Main thread → heartbeats
```

### Step 4 — `Dockerfile`

Build context must be the repository root so `controller_components/` is available:

```dockerfile
FROM python:3.9-slim

# Install the node-side framework package
COPY controller_components/controlled_entity/ /tmp/controlled_entity/
RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

# Install any node-specific Python dependencies
# RUN pip install "my-library<2"

WORKDIR /node

COPY network_nodes/my_domain/my_node/*.py   ./
COPY network_nodes/my_domain/my_node/*.conf ./

CMD ["python3", "node.py"]
```

### Step 5 — Add a service block to the root `docker-compose.yml`

Nodes do not have their own `docker-compose.yml`. Instead, add a service block to the
root `docker-compose.yml` (see `amp1_node` for the exact pattern):

```yaml
# In the root docker-compose.yml — under services:
my_node:
  container_name: my_node
  build:
    context: ./
    dockerfile: network_nodes/my_domain/my_node/Dockerfile
  volumes:
    - ./network_nodes/my_domain/my_node/:/node
  networks:
    - aic_network
  depends_on:
    - aic_register
    - node_msg_broker
  command: >
    sh -c "sleep 5 && python3 node.py"
  environment:
    - PYTHONUNBUFFERED=1
```

The `sleep 5` gives the register and broker time to start before the node connects.

---

## Auto-Generated REST API and MCP Tools

Once `AicController(with_api=True).run()` is called, the following are created
automatically for each `@aic_app`-decorated class:

### REST Endpoints (served on port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/apps` | List all registered apps |
| GET | `/apps/{AppName}/info` | App configuration |
| GET | `/apps/{AppName}/state` | Current state (`idle` / `running`) |
| PUT | `/apps/{AppName}/state` | Change state: `{"state": "running"}` |
| GET | `/apps/{AppName}/measurements` | Latest measurements buffer |
| POST | `/apps/{AppName}/control` | Send a manual command |

### MCP Tools (served on port 8000/mcp)

| Tool name | Description |
|-----------|-------------|
| `{AppName}_get_measurements` | Get latest measurements |
| `{AppName}_get_state` | Get app state |
| `{AppName}_set_state` | Set app state |
| `{AppName}_{cmd_lower}` | One tool per command in `control_functions` |
| `{AppName}_{name}` | One tool per `@agent_controlled` method |

Tools are usable by any MCP-compatible AI agent (e.g. Claude via OpenCode):

```bash
opencode   # from the repository root, uses opencode.json for MCP config
```

---

## Conflict Mitigation Pattern

When multiple apps compete to send commands to the same node, use a dedicated
`ConflictMitigator` app (see `control_application_v2_example/aic_app.py`):

1. Give it the highest `aic_app_id` so it runs last in each cycle.
2. In `process()`, drain `send_commands` from the managed apps.
3. Group by `(node_id, command_name)` and apply a priority policy.
4. Re-queue the winning command via `cls.add_command()`.

The mitigator must declare `control_functions` for every node it may re-dispatch to.

---

## Quick Reference: What to Import

Always import from the installed package names — never from `controller_components/`
relative paths.

```python
# Control application
from ai_nn_controller.decorators.aic_app        import aic_app
from ai_nn_controller.decorators.command_validator import command_validator
from ai_nn_controller.decorators.agent_controlled import agent_controlled
from ai_nn_controller.AicApp                    import AicApp
from ai_nn_controller.AicController             import AicController
from ai_nn_controller.registry                  import register_command
from ai_nn_controller.managers.AicManager       import AicManager  # for conflict mitigation

# Plugin
from ai_nn_controller.plugin_framework import AicPlugin, aic_plugin
from ai_nn_controller.plugin_framework import StoragePlugin, ModelRegistryPlugin, MonitoringPlugin

# Network node
from controlled_entity import ControlledEntity, node, NodeRunner
```

---

## Checklist: New Control Application

- [ ] Directory created under `control_applications/<name>/`
- [ ] `aic_app.conf` with `ip_address = aic_register` and `register_port = 5558`
- [ ] `commands.py` with handlers + schemas + `register_command()` calls
- [ ] `aic_app.py` imports `commands` before `@aic_app`, defines `aic_app_id` (unique), `read_measurements` (dict), `control_functions` (dict), `process(cls, measurements)` classmethod, and calls `AicController(with_api=True).run()` in `__main__`
- [ ] `pyproject.toml` with `ai_nn_controller.app_init` entry point
- [ ] `Dockerfile` with build context set to repository root; install order: framework → plugins → app
- [ ] `docker-compose.yml` inside the app folder, using `aic_network: external: true`

## Checklist: New Plugin

- [ ] Directory created under `plugins/<name>/`
- [ ] `aic_plugin.py` subclasses `AicPlugin` (or a typed mixin), decorated with `@aic_plugin(name="...", plugin_type="...")`
- [ ] `pyproject.toml` with `ai_nn_controller.plugin_init` entry point
- [ ] `Dockerfile` — build context is repo root; installs `ai_nn_controller` then the plugin package
- [ ] Plugin added to every consuming app's `Dockerfile` (before app install) and volume-mounted in the root `docker-compose.yml` `aic_server` service

## Checklist: New Network Node

- [ ] Directory created under `network_nodes/<domain>/<name>/`
- [ ] `node.conf` with `ip_address`, `register_port`, unique `node_id`, `pub_port`
- [ ] `node.py` subclasses `ControlledEntity`, decorated with `@node(name="...")`, implements `poll_measurements()`, optionally `handle_command()` and `setup()`; calls `NodeRunner().run()` in `__main__`
- [ ] `Dockerfile` — build context is repo root; copies and installs `controlled_entity` from `controller_components/`
- [ ] Service block added to the root `docker-compose.yml` with `depends_on: [aic_register, node_msg_broker]` and `sleep 5` startup delay

---

## Template Generator (after stack is running)

The register service can auto-generate a skeleton control application from the currently
registered nodes:

```bash
docker compose up -d
docker exec -it aic_register python3 /register/generate_template_app.py \
  --app-name my_app \
  --app-id 100 \
  --update-time 2 \
  --output-root /control_applications \
  --compose-output /workspace/docker-compose-my_app.yml
```

This creates `control_applications/my_app/` with all boilerplate pre-filled from live
node registrations.

---

## What NOT to Do

- Do not edit anything under `controller_components/`.
- Do not import from `controller_components/` using relative or filesystem paths; always
  use the installed package names (`ai_nn_controller`, `controlled_entity`).
- Do not create a control application, plugin, or network node without a `Dockerfile` in
  its directory.
- Do not give a network node or plugin its own `docker-compose.yml` — nodes are wired into
  the root `docker-compose.yml`; plugins are installed as packages inside the app container.
- Do not create a control application without a `docker-compose.yml` in its directory.
- Do not hardcode broker or register IPs in application code; they come from `aic_app.conf`
  and `node.conf`.
- Do not duplicate `aic_app_id` or `node_id` values across apps/nodes in the same stack.
- Do not run a control application or node without `aic_register` and `node_msg_broker`
  already up (use `depends_on` in compose and a startup `sleep`).
- Do not send commands from `process()` using raw ZMQ; always use `cls.add_command()`.
- Do not place `@command_validator` or `@agent_controlled` above `@classmethod`; the
  `@classmethod` decorator must be the outermost one.
