MCP Integration
===============

ai_nn_controller automatically generates MCP (Model Context Protocol) tools for AI agent
integration, enabling AI agents such as Claude to discover and control network
equipment without any extra configuration.

Overview
--------

MCP tools are auto-generated from:

- Application ``control_functions`` → Control tools
- Application ``read_measurements`` → Measurement tools
- Application state management → State tools
- ``@agent_controlled`` decorated methods → Agent-controlled tools

MCP Endpoints
-------------

Server Info
~~~~~~~~~~~

.. http:get:: /mcp/

   Get MCP server information.

   **Response:**

   .. code-block:: json

      {
        "name": "aic-controller",
        "version": "1.0.0",
        "protocol": "MCP",
        "transport": "HTTP/SSE",
        "stats": {
          "total_tools": 8,
          "total_apps": 2,
          "apps": ["NetworkApp1", "NetworkApp2"],
          "tools_by_type": {"control": 2, "measurement": 2, "state": 4, "agent_controlled": 0}
        }
      }

List All Tools
~~~~~~~~~~~~~~

.. http:get:: /mcp/tools

   List all registered MCP tools.

   **Response:**

   .. code-block:: json

      {
        "tools": [
          {
            "name": "NetworkApp1_set_gain",
            "description": "Set amplifier gain. App: NetworkApp1, Nodes: [8]",
            "inputSchema": {
              "type": "object",
              "properties": {
                "node_id": {"type": "integer", "enum": [8]},
                "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
                "target_gain": {"type": "number"}
              },
              "required": ["node_id", "target_gain"]
            }
          }
        ],
        "count": 1
      }

List Tools by App
~~~~~~~~~~~~~~~~~

.. http:get:: /mcp/tools/{app_name}

   List MCP tools for a specific application.

   :param app_name: Name of the application

   **Response:** Same tools format, with app and count

   .. code-block:: json

      {
        "app": "NetworkApp1",
        "tools": [
          {
            "name": "NetworkApp1_set_gain",
            "description": "Set amplifier gain. App: NetworkApp1, Nodes: [8]",
            "inputSchema": {
              "type": "object",
              "properties": {
                "node_id": {"type": "integer", "enum": [8]},
                "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
                "target_gain": {"type": "number"}
              },
              "required": ["node_id", "target_gain"]
            }
          }
        ],
        "count": 1
      }

Call Tool
~~~~~~~~~

.. http:post:: /mcp/tools/call

   Execute an MCP tool.

   **Request Body:**

   .. code-block:: json

      {
        "name": "NetworkApp1_set_state",
        "arguments": {
          "state": "running"
        }
      }

   **Response:**

   .. code-block:: json

      {
        "success": true,
        "result": {
          "app": "NetworkApp1",
          "state": "running",
          "previous_state": "stopped"
        }
      }

   **Error Response:**

   .. code-block:: json

      {
        "success": false,
        "error": "Tool 'unknown_tool' not found"
      }

   **Rejected Response (Validation Failed):**

   If the application has a command validator that rejects the command:

   .. code-block:: json

      {
        "success": true,
        "result": {
          "app": "NetworkApp1",
          "node_id": 8,
          "command": {"command": "SET_GAIN", "payload": {"target_gain": 30.0}},
          "status": "rejected",
          "reason": "target_gain 30.0 dB exceeds maximum of 25.0 dB"
        }
      }

   .. note::

      Command validators are optional guardrails. If no validator is defined
      for a command, it passes through unchanged. See
      :doc:`../user_guide/developing_apps` for details.

MCP JSON-RPC
~~~~~~~~~~~~

.. http:post:: /mcp/message

   Raw MCP JSON-RPC 2.0 endpoint.

   **Request Body:**

   .. code-block:: json

      {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
      }

   **Response:**

   .. code-block:: json

      {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
          "tools": [...]
        }
      }

   Supported methods:

   - ``initialize`` - Initialize MCP connection
   - ``tools/list`` - List available tools
   - ``tools/call`` - Execute a tool
   - ``ping`` - Health check

Server-Sent Events
~~~~~~~~~~~~~~~~~~

.. http:get:: /mcp/sse

   Server-Sent Events stream for real-time updates.

   Used for push notifications from the server.

Auto-Generated Tools
--------------------

For each ``@aic_app``, the following tools are generated:

Control Tools
~~~~~~~~~~~~~

One tool per command in ``control_functions``:

- **Name**: ``{AppName}_{command_name}``
- **Example**: ``NetworkApp1_set_gain``
- **Schema**: From command registry schema

Measurement Tool
~~~~~~~~~~~~~~~~

If app has ``read_measurements``:

- **Name**: ``{AppName}_get_measurements``
- **Schema**: Optional ``node_id`` filter

State Tools
~~~~~~~~~~~

For every app:

- ``{AppName}_get_state`` - Get current state
- ``{AppName}_set_state`` - Set state (running/paused/stopped)

Agent-Controlled Tools
~~~~~~~~~~~~~~~~~~~~~~

If the app has ``@agent_controlled`` decorated methods, one tool per operation:

- **Name**: ``{AppName}_{operation_name}``
- **Example**: ``SmartApp_optimize_gain``
- **Schema**: From the ``schema`` parameter of the ``@agent_controlled`` decorator

These tools execute **inside the process loop** with access to live measurements.
The app must be in ``running`` state for these tools to work.

**Request:**

.. code-block:: json

   {
     "name": "SmartApp_optimize_gain",
     "arguments": {
       "node_id": 8,
       "strategy": "max_snr"
     }
   }

**Response:**

.. code-block:: json

   {
     "success": true,
     "result": {
       "result": {
         "status": "applied",
         "previous_gain": 15.0,
         "new_gain": 17.0
       },
       "request_id": "abc-123-def"
     }
   }

**Error (app not running):**

.. code-block:: json

   {
     "success": true,
     "result": {
       "error": "App 'SmartApp' is not running (state: stopped). Start the app first."
     }
   }

**Error (timeout):**

.. code-block:: json

   {
     "success": true,
     "result": {
       "error": "Timeout waiting for operation 'optimize_gain' (request_id=abc-123, timeout=11s)."
     }
   }

Tool Registry API
-----------------

.. py:class:: ai_nn_controller.mcp.tool_registry.MCPToolRegistry

   Central registry for MCP tools.

   .. py:method:: register_tool(tool)
      :classmethod:

      Register an MCP tool.

   .. py:method:: list_tools()
      :classmethod:

Tool Schema Lookup
------------------

.. http:get:: /mcp/schema/{tool_name}

   Get the JSON schema for a specific tool.

   **Response:**

   .. code-block:: json

      {
        "name": "NetworkApp1_set_gain",
        "description": "Set amplifier gain. App: NetworkApp1, Nodes: [8]",
        "inputSchema": {
          "type": "object",
          "properties": {
            "node_id": {"type": "integer", "enum": [8]},
            "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
            "target_gain": {"type": "number"}
          },
          "required": ["node_id", "target_gain"]
        },
        "app": "NetworkApp1",
        "type": "control"
      }

      List all tools in MCP format.

   .. py:method:: list_tools_by_app(app_name)
      :classmethod:

      List tools for a specific app.

   .. py:method:: call_tool(name, arguments)
      :classmethod:
      :async:

      Execute a tool by name.

   .. py:method:: get_stats()
      :classmethod:

      Get registry statistics.

.. py:class:: ai_nn_controller.mcp.tool_registry.MCPTool

   Represents a single MCP tool.

   :param name: Tool name
   :param description: Human-readable description
   :param input_schema: JSON Schema for input validation
   :param handler: Async function to execute the tool
   :param app_name: Associated application name
   :param tool_type: "control", "measurement", "state", or "agent_controlled"

   .. py:method:: to_mcp_format()

      Convert to MCP protocol format.

Claude Desktop Integration
--------------------------

To integrate with Claude Desktop, add to your MCP configuration file:

.. code-block:: json

   {
     "mcpServers": {
       "ai_nn_controller": {
         "command": "curl",
         "args": ["-X", "POST", "http://localhost:8000/mcp/message"]
       }
     }
   }

Or use the HTTP transport directly in Claude's settings.

Example Usage with AI Agents
----------------------------

An AI agent can:

1. **Discover tools**: Query ``/mcp/tools`` to see available capabilities
2. **Read state**: Call ``{App}_get_state`` to check if app is running
3. **Start app**: Call ``{App}_set_state`` with ``{"state": "running"}``
4. **Read measurements**: Call ``{App}_get_measurements``
5. **Send commands**: Call ``{App}_set_gain`` or other control tools
6. **Run in-loop operations**: Call ``{App}_optimize_gain`` or other agent-controlled tools

Example conversation:

.. code-block:: text

   User: "Check the gain on node 3"
   Agent: [Calls NetworkApp1_get_measurements with node_id=3]
   Agent: "The current gain on node 3 is 20.5 dB"

   User: "Set it to 15 dB"
   Agent: [Calls NetworkApp1_set_gain with node_id=3, target_gain=15]
   Agent: "Done. I've set the target gain to 15 dB"

MCP Server Implementation
-------------------------

.. py:class:: ai_nn_controller.mcp.server.MCPServer

   MCP Server that exposes AIC tools to AI agents.

   .. py:method:: handle_request(request)
      :async:

      Handle an MCP protocol request.

.. py:class:: ai_nn_controller.mcp.server.StdioMCPServer

   MCP Server with stdio transport for Claude Desktop.

   .. py:method:: run()
      :async:

      Run the server, reading from stdin and writing to stdout.
