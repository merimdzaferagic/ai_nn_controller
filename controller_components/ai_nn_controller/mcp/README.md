# MCP Integration for ai_nn_controller

This module provides automatic MCP (Model Context Protocol) tool generation for ai_nn_controller, enabling AI agents to control any type of network node (optical, wireless, RAN, core, etc.) through a standardized interface.

## Overview

The MCP integration automatically generates tools from your `@aic_app` decorated classes. When you define an AIC app with measurements and control functions, the framework creates corresponding MCP tools that AI agents can discover and invoke.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer writes:                         │
│  @aic_app(name="PowerBalancer")                             │
│  class PowerBalancer(AicApp):                               │
│      read_measurements = {3: ["gain", "power"]}             │
│      control_functions = {3: ["SET_GAIN"], 8: ["SET_VOA"]}  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Framework auto-generates MCP tools:            │
│  - PowerBalancer_set_gain (node 3)                          │
│  - PowerBalancer_set_voa (node 8)                           │
│  - PowerBalancer_get_measurements                           │
│  - PowerBalancer_get_state                                  │
│  - PowerBalancer_set_state                                  │
│  - PowerBalancer_optimize_gain (@agent_controlled)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              AI Agent invokes tools:                        │
│  "Set the gain on node 3 to 15 dB"                          │
│  → calls PowerBalancer_set_gain(node_id=3, target_gain=15)  │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### 1. Define Your AIC App (No Changes Required)

```python
from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.AicApp import AicApp

@aic_app(name="MyNetworkApp")
class MyNetworkApp(AicApp):
    # Define which measurements to read from which nodes
    read_measurements = {
        3: ["amp_target_gain", "amp_gain_tilt"],
        8: ["roadm_preamp_gain", "roadm_booster_gain"],
    }

    # Define which control functions are available on which nodes
    control_functions = {
        3: ["SET_GAIN", "SET_TILT"],
        8: ["SET_GAIN", "SET_VOA"],
    }

    @classmethod
    def process(cls, measurements):
        # Your custom control logic
        pass
```

The framework automatically generates these MCP tools:
- `MyNetworkApp_set_gain` - Control amplifier gain on nodes 3 and 8
- `MyNetworkApp_set_tilt` - Control spectral tilt on node 3
- `MyNetworkApp_set_voa` - Control VOA attenuation on node 8
- `MyNetworkApp_get_measurements` - Read telemetry from nodes 3 and 8
- `MyNetworkApp_get_state` - Get app state (running/paused/stopped)
- `MyNetworkApp_set_state` - Control app lifecycle

### 1.1 Add Command Validators (Optional)

You can add optional validation logic to enforce guardrails on MCP tool calls. This is useful for enforcing safety limits when AI agents control your network.

```python
from ai_nn_controller.decorators.command_validator import command_validator

@aic_app(name="MyNetworkApp")
class MyNetworkApp(AicApp):
    control_functions = {3: ["SET_GAIN"]}

    # Safety limit
    MAX_GAIN = 25.0

    @command_validator("SET_GAIN")
    @classmethod
    def validate_set_gain(cls, params: dict) -> tuple[bool, str | None]:
        """Validate SET_GAIN commands from MCP tools."""
        target_gain = params.get("target_gain", 0)
        if target_gain > cls.MAX_GAIN:
            return False, f"Gain {target_gain} exceeds max {cls.MAX_GAIN} dB"
        return True, None
```

When an MCP tool call fails validation, the response will include:
```json
{
  "status": "rejected",
  "reason": "Gain 30.0 exceeds max 25.0 dB"
}
```

**Note:** Validators are completely optional. If no validator is defined for a command, MCP tool calls pass through unchanged.

### 1.2 Add Agent-Controlled Operations (Optional)

Agent-controlled operations let MCP tools execute logic **inside the process loop** with access to live measurements. Unlike control tools (which bypass `process()`), these handlers are synchronized with the control cycle.

```python
from ai_nn_controller.decorators.agent_controlled import agent_controlled

@aic_app(name="MyNetworkApp")
class MyNetworkApp(AicApp):
    read_measurements = {8: ["preamp_gain"]}
    control_functions = {8: ["SET_GAIN"]}

    @classmethod
    @agent_controlled(
        name="optimize_gain",
        description="Optimize gain based on live measurements",
        schema={
            "properties": {
                "node_id": {"type": "integer"},
                "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
            },
            "required": ["node_id", "strategy"]
        }
    )
    def handle_optimize_gain(cls, request, measurements):
        """Handler receives MCP args + live measurements, returns result to caller."""
        node_id = request["node_id"]
        latest = measurements.get(node_id, [{}])[-1] or {}
        new_gain = latest.get("preamp_gain", 15) + 2.0
        cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"target_gain": new_gain}}))
        return {"status": "applied", "new_gain": new_gain}
```

This generates `MyNetworkApp_optimize_gain`. The app must be `running` for the tool to work.

### Agent-Controlled Tool Response

```json
{
  "success": true,
  "result": {
    "result": {"status": "applied", "new_gain": 17.0},
    "request_id": "abc-123-def"
  }
}
```

### 2. Access MCP Tools via HTTP

The FastAPI server exposes MCP endpoints at `/mcp/*`:

```bash
# List all available tools
curl http://localhost:8000/mcp/tools

# Get tools for a specific app
curl http://localhost:8000/mcp/tools/MyNetworkApp

# Call a tool
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "MyNetworkApp_set_gain", "arguments": {"node_id": 3, "target_gain": 15.0}}'

# Get schema for a tool
curl http://localhost:8000/mcp/schema/MyNetworkApp_set_gain
```

### 3. Use with Claude Desktop (stdio transport)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai_nn_controller": {
      "command": "python",
      "args": ["/path/to/run_mcp_server.py"],
      "env": {}
    }
  }
}
```

Then run:
```bash
python run_mcp_server.py
```

## Generated Tool Schemas

### Control Tools

Each control function generates a tool with a schema based on the command type:

**SET_GAIN**
```json
{
  "name": "AppName_set_gain",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "integer", "enum": [3, 8]},
      "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
      "target_gain": {"type": "number"}
    },
    "required": ["node_id", "target_gain"]
  }
}
```

**SET_VOA**
```json
{
  "name": "AppName_set_voa",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "integer"},
      "channel": {"type": "integer"},
      "attenuation": {"type": "number"},
      "direction": {"type": "string", "enum": ["mux", "demux"]}
    },
    "required": ["node_id", "channel", "attenuation"]
  }
}
```

**SET_TILT**
```json
{
  "name": "AppName_set_tilt",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "integer"},
      "tilt_value": {"type": "number"}
    },
    "required": ["node_id", "tilt_value"]
  }
}
```

### Measurement Tools

```json
{
  "name": "AppName_get_measurements",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "integer", "enum": [3, 4, 5]}
    },
    "required": []
  }
}
```

### State Management Tools

```json
{
  "name": "AppName_set_state",
  "inputSchema": {
    "type": "object",
    "properties": {
      "state": {"type": "string", "enum": ["running", "paused", "stopped"]}
    },
    "required": ["state"]
  }
}
```

### Agent-Controlled Tools

Generated from `@agent_controlled` decorated methods. The schema comes from the decorator's `schema` parameter:

```json
{
  "name": "AppName_optimize_gain",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "integer"},
      "strategy": {"type": "string", "enum": ["max_snr", "min_power"]}
    },
    "required": ["node_id", "strategy"]
  }
}
```

## Architecture

```
ai_nn_controller/mcp/
├── __init__.py           # Module exports
├── schemas.py            # JSON Schema definitions for commands
├── tool_registry.py      # Central registry for MCP tools
├── tool_generator.py     # Auto-generates tools from @aic_app
├── server.py             # MCP server implementation (stdio)
├── fastapi_integration.py # FastAPI router for HTTP/SSE transport
└── README.md             # This file
```

## Adding New Command Types

To add support for new command types:

1. Add the command to `CommandHandler` enum in `enums/CommandHandler.py`
2. Add the handler function in `managers/CommandManager.py`
3. Add the schema definition in `mcp/schemas.py`:

```python
COMMAND_SCHEMAS["NEW_COMMAND"] = {
    "description": "Description of what this command does",
    "properties": {
        "node_id": {"type": "integer"},
        "param1": {"type": "number", "description": "..."},
        # ... more parameters
    },
    "required": ["node_id", "param1"]
}
```

The framework will automatically generate MCP tools for any app that uses the new command.

## API Reference

### MCPToolRegistry

```python
from ai_nn_controller.mcp import MCPToolRegistry

# List all tools
tools = MCPToolRegistry.list_tools()

# Get a specific tool
tool = MCPToolRegistry.get_tool("AppName_set_gain")

# Call a tool
result = await MCPToolRegistry.call_tool("AppName_set_gain", {"node_id": 3, "target_gain": 15})

# Get registry statistics
stats = MCPToolRegistry.get_stats()
```

### MCPToolGenerator

```python
from ai_nn_controller.mcp import MCPToolGenerator

# Generate tools for an app (usually called by @aic_app decorator)
tools = MCPToolGenerator.generate_tools_for_app(
    app_name="MyApp",
    app_class=MyAppClass,
    manager_class=AicManager
)
```
