# FastAPI Client for AIC Controller

This package provides a Python client interface for interacting with the
AIC (AI Controller) FastAPI server. It includes both programmatic API access
and an interactive command-line interface.

## Features

- **Complete API Coverage**: All FastAPI endpoints (plus MCP) accessible via Python
- **Easy to Use**: Simple, intuitive client interface
- **Interactive CLI**: Command-line interface for manual control
- **Dockerized**: Ready-to-use Docker container
- **Well Documented**: Comprehensive examples and usage guides

## Components

### 1. `client.py` - Core API Client

The main client class `AicApiClient` provides methods for:
- Health checks and API information
- App lifecycle management (start, stop, pause, resume)
- Fetching measurements from nodes
- Sending control commands
- MCP tool discovery and execution
- Convenience methods for common operations

### 2. `examples.py` - Usage Examples

Demonstrates all major client functionality:
- Basic operations (health, list apps)
- App lifecycle management
- Measurement fetching
- Control command sending
- Convenience methods

### 3. `cli.py` - Interactive CLI

`AicCli`, a `cmd.Cmd`-based interactive shell (prompt `aic> `) with commands:
- `list` - List all apps
- `appinfo/state` - Inspect a specific app
- `start/stop/pause/resume` - Control app states
- `measurements/node` - View measurements
- `control` - Send control commands
- `status` - Print detailed app status
- `health/info` - API health and info
- `exit`/`quit`

## Installation

### Option 1: Docker (Recommended)

This client is one of the services in the repo-root Compose files. From the
repo root:

```bash
# Optical dummy-node stack
docker compose up -d

# or the srsRAN stack
docker compose -f docker-compose.srsran.yml up -d
```

In `docker-compose.yml`, the `fastapi_client` service depends on `aic_server`;
in `docker-compose.srsran.yml`, it depends on `srsran_reader` instead. Either
way the FastAPI server it talks to is reachable at `http://<server-service>:8000`
from inside the Docker network, or `http://localhost:8000` from the host.

### Option 2: Local Installation

```bash
cd fastapi_client
pip install -r requirements.txt
```

## Usage

### Programmatic Usage

```python
from client import AicApiClient

# Create client
client = AicApiClient(base_url="http://localhost:8000")

# List all apps
apps = client.list_apps()
for app in apps:
    print(f"{app.name}: {app.state}")

# Start an app
client.start_app("NetworkApp1")

# Get measurements
measurements = client.get_measurements("NetworkApp1")
print(measurements)

# Send control command
client.send_control(
    app_name="NetworkApp1",
    node_id=8,
    command="SET_GAIN",
    payload={"amp_type": "preamp", "target_gain": 12}
)

# Stop the app
client.stop_app("NetworkApp1")
```

### Interactive CLI Usage

#### With Docker:

```bash
# Attach to the client container
docker exec -it fastapi_client python3 cli.py

# Or use bash for more control
docker exec -it fastapi_client bash
python3 cli.py
```

#### Local:

```bash
python3 cli.py --url http://localhost:8000
```

#### CLI Commands:

```
aic> help                    # Show all commands
aic> list                    # List all apps
aic> appinfo NetworkApp1     # Get app details
aic> start NetworkApp1       # Start an app
aic> measurements NetworkApp1  # Get measurements
aic> control NetworkApp1 8 SET_GAIN '{"amp_type":"preamp","target_gain":12}'
aic> stop NetworkApp1        # Stop the app
aic> exit                    # Exit CLI
```

### Examples Script

#### With Docker:

```bash
docker exec -it fastapi_client python3 examples.py
```

#### Local:

```bash
python3 examples.py
```

## API Reference

### AicApiClient

#### Initialization

```python
client = AicApiClient(base_url="http://localhost:8000", timeout=10)
```

#### Health & Info

- `health_check()` - Check API health
- `get_api_info()` - Get API information

#### App Management

- `list_apps()` - List all registered apps
- `get_app_info(app_name)` - Get app configuration
- `get_app_state(app_name)` - Get current state
- `set_app_state(app_name, state)` - Set app state
- `start_app(app_name)` - Start an app
- `stop_app(app_name)` - Stop an app
- `pause_app(app_name)` - Pause an app
- `resume_app(app_name)` - Resume an app

#### Measurements

- `get_measurements(app_name)` - Get all measurements
- `get_node_measurement(app_name, node_id)` - Get specific node data

#### Control Commands

- `send_control(app_name, node_id, command, payload)` - Send control command

#### MCP

- `mcp_get_info()` / `mcp_list_tools()` / `mcp_list_tools_by_app(app_name)`
- `mcp_get_tool(tool_name)` / `mcp_get_tool_schema(tool_name)`
- `mcp_call_tool(tool_name, arguments)` / `mcp_send_message(method, params)`
- `mcp_set_gain/mcp_set_voa/mcp_set_tilt/mcp_get_measurements/mcp_get_state/mcp_set_state`
- `mcp_start_app/mcp_stop_app/mcp_pause_app`
- `mcp_print_tools(app_name=None)` / `mcp_validate_tool_call(tool_name, arguments)`

#### Convenience Methods

- `wait_for_state(app_name, expected_state, timeout, poll_interval)` - Wait for state
- `start_app_and_wait(app_name, timeout)` - Start and wait
- `print_app_status(app_name)` - Print detailed status

## Docker Setup

### Docker Compose Configuration

The root `docker-compose.yml` includes:

1. **redis** - state storage
2. **aic_register** - node/app registration service
3. **node_msg_broker** - ZMQ message broker
4. **amp1_node / roadm1_node / amp2_node / amp3_node / roadm2_node / roadm3_node** - six dummy optical nodes
5. **aic_server** - the FastAPI + MCP server (runs `control_applications/control_application_v2_example`)
6. **fastapi_client** - this client, as an interactive shell container

(`docker-compose.srsran.yml` swaps the six dummy nodes for a single `srsran_node`
and `aic_server` for `srsran_reader`.)

All containers are connected via the `aic_network` bridge network.

### Client Container

The client container:
- Depends on the server container being started (`depends_on`)
- Stays running for interactive access (`command: "/bin/bash"` by default in
  compose; the Dockerfile's own default is `python3 cli.py`)
- Has all client tools pre-installed
- Mounts the source directory for live development

## Testing

### Quick Test

```bash
# Start the environment
docker compose up -d

# Wait for services to be ready
sleep 25

# Run examples
docker exec -it fastapi_client python3 examples.py

# Or start interactive CLI
docker exec -it fastapi_client python3 cli.py
```

### Step-by-Step Testing

1. **Start the environment**:
   ```bash
   docker compose up -d --build
   ```

2. **Wait for initialization** (check logs):
   ```bash
   docker logs aic_server
   # Look for the FastAPI/uvicorn startup lines and controller init messages
   ```

3. **Attach to client container**:
   ```bash
   docker exec -it fastapi_client bash
   ```

4. **Run examples**:
   ```bash
   python3 examples.py
   ```

5. **Try interactive CLI**:
   ```bash
   python3 cli.py
   ```

6. **Test API directly** (from host):
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/apps
   ```

## Development

### Adding New Client Methods

Edit `client.py` and add methods to the `AicApiClient` class:

```python
def my_new_method(self, arg1, arg2):
    """Description of what this method does."""
    return self._make_request('GET', f'/my/endpoint/{arg1}', json={'arg2': arg2})
```

### Adding CLI Commands

Edit `cli.py` and add command methods:

```python
def do_mycommand(self, arg):
    """Description: mycommand <arg>"""
    try:
        result = self.client.my_new_method(arg)
        print(f"\nResult: {result}\n")
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
```

## Troubleshooting

### Cannot Connect to API

1. Check if the FastAPI server is running:
   ```bash
   docker logs aic_server
   curl http://localhost:8000/health
   ```

2. Verify network connectivity:
   ```bash
   docker exec fastapi_client ping aic_server
   ```

3. Check the base URL in client code:
   - Inside Docker: `http://aic_server:8000` (or `http://srsran_reader:8000`)
   - From host: `http://localhost:8000`

### CLI Commands Not Working

1. Ensure app names are correct:
   ```bash
   aic> list
   ```

2. Check app states:
   ```bash
   aic> state NetworkApp1
   ```

3. View detailed status:
   ```bash
   aic> status NetworkApp1
   ```

### Docker Container Exits Immediately

The client container is designed to stay running for interactive use. If it exits:

1. Check logs:
   ```bash
   docker logs fastapi_client
   ```

2. Verify dependencies:
   ```bash
   docker compose ps
   ```

## Examples

### Example 1: Monitor All Apps

```python
from client import AicApiClient
import time

client = AicApiClient()

while True:
    apps = client.list_apps()
    for app in apps:
        print(f"{app.name}: {app.state}")
        if app.state == "running":
            measurements = client.get_measurements(app.name)
            print(f"  Measurements: {len(measurements)} nodes")
    time.sleep(5)
```

### Example 2: Automated Control

```python
from client import AicApiClient

client = AicApiClient()

# Start app
client.start_app("NetworkApp1")
client.wait_for_state("NetworkApp1", "running")

# Send control command every 10 seconds
for i in range(10):
    client.send_control(
        "NetworkApp1",
        8,
        "SET_GAIN",
        {"amp_type": "preamp", "target_gain": 10 + i}
    )
    time.sleep(10)

# Stop app
client.stop_app("NetworkApp1")
```

### Example 3: Measurement Analysis

```python
from client import AicApiClient
import time

client = AicApiClient()

# Start app and collect measurements
client.start_app("NetworkApp1")
time.sleep(10)

measurements = client.get_measurements("NetworkApp1")

# Analyze measurements from node 3 (Amp1)
node_data = measurements.get("3")
if node_data:
    gain = node_data.get("amp1_target_gain")
    print(f"Current gain: {gain}")

    if gain < 10:
        print("Gain too low, sending adjustment command")
        client.send_control(
            "NetworkApp1",
            8,
            "SET_GAIN",
            {"amp_type": "preamp", "target_gain": 12}
        )
```

## Architecture

```
┌──────────────────┐
│  Python Client   │
│  (fastapi_client)│
└────────┬─────────┘
         │ HTTP/REST + MCP
         │
         ▼
┌──────────────────┐
│  FastAPI Server  │
│  (aic_server)    │
└────────┬─────────┘
         │ ZMQ
         │
         ▼
┌──────────────────┐
│  Message Broker  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Network Nodes   │
└──────────────────┘
```

## License

Dual-licensed under AGPL (see repo-root `LICENSE`) or commercial licence
(see repo-root `LICENSE-COMMERCIAL.md`, contact infoknex@tcd.ie).

## Support

For issues or questions:
1. Check the examples in `examples.py`
2. Review the Sphinx docs (`docs/api/rest_api.rst`, `docs/api/mcp.rst`)
3. Check FastAPI docs at `http://localhost:8000/docs`
