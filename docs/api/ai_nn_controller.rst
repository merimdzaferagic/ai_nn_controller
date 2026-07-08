Core Framework API (ai_nn_controller)
======================================

This is the API reference for the core ``ai_nn_controller`` package — the
control-plane half of ai_nn_controller.

The framework is domain-agnostic and supports any type of network node — optical,
wireless, RAN, core network, and more.

AicApp
------

.. py:class:: ai_nn_controller.AicApp

   Base class for AIC control applications.

   **Required Class Attributes:**

   .. py:attribute:: aic_app_id
      :type: int

      Unique identifier for this application instance.

   .. py:attribute:: control_loop_update_time
      :type: int

      Interval in seconds between process() calls. Default: 1

   .. py:attribute:: read_measurements
      :type: dict

      Dictionary mapping node IDs to lists of measurement names to subscribe to.
      Example: ``{3: ["gain", "power"]}``

   .. py:attribute:: control_functions
      :type: dict

      Dictionary mapping node IDs to lists of available command names.
      Example: ``{3: ["SET_GAIN"]}``

   **Auto-Generated Attributes (set by @aic_app decorator):**

   .. py:attribute:: cell_ids
      :type: list

      List of node IDs this application monitors. Auto-derived from
      the union of ``read_measurements`` and ``control_functions`` keys.

   .. py:attribute:: send_commands
      :type: deque

      Queue of commands to be sent. Auto-initialized as an empty ``deque`` by the
      ``@aic_app`` decorator.

   **Methods:**

   .. py:method:: add_command(command)
      :classmethod:

      Add a command to the send queue.

      :param command: Tuple of (command_name, payload_dict)
      :type command: tuple

      Example::

          cls.add_command((
              "SET_GAIN",
              {"node_id": 8, "value": {"target_gain": 20.0}}
          ))

   .. py:method:: process(measurements)
      :classmethod:

      Process incoming measurements. Override this method in your subclass.

      :param measurements: Dict keyed by node_id with lists of measurement dicts
      :type measurements: dict

AicController
-------------

.. py:class:: ai_nn_controller.AicController(with_api=False, api_host="0.0.0.0", api_port=8000, verbose=False)

   Runtime engine that manages application lifecycle and message routing.

   :param with_api: Enable FastAPI server (default: False)
   :param api_host: Host address for API server (default: "0.0.0.0")
   :param api_port: Port for API server (default: 8000)
   :param verbose: Enable verbose logging (default: False)

   **Methods:**

   .. py:method:: run()

      Start the controller. If with_api=True, starts FastAPI server.
      This method blocks until interrupted.

   .. py:method:: update_app_state(app_name, state)

      Update the state of an application.

      :param app_name: Name of the application
      :param state: New state - "running", "paused", or "stopped"
      :returns: Dict with app name, new state, and previous state
      :raises ValueError: If app doesn't exist or state is invalid

   .. py:method:: get_app_state(app_name)

      Get current state of an application.

      :param app_name: Name of the application
      :returns: Current state string
      :raises ValueError: If app doesn't exist

   .. py:method:: get_app_measurements(app_name)

      Get latest measurements for an application.

      :param app_name: Name of the application
      :returns: Dict mapping node_id to latest measurement
      :raises ValueError: If app doesn't exist

   .. py:method:: send_manual_control(app_name, node_id, command)

      Send a manual control command.

      :param app_name: Name of the application
      :param node_id: Target node ID
      :param command: Command specification dict
      :returns: Result dict with status

@aic_app Decorator
------------------

.. py:decorator:: ai_nn_controller.decorators.aic_app.aic_app(name)

   Decorator that registers an AIC application with the framework.

   :param name: Unique name for the application

   This decorator:

   1. Registers the app with AicManager
   2. Creates FastAPI REST endpoints
   3. Auto-generates MCP tools based on capabilities
   4. Scans for @command_validator decorated methods
   5. Scans for @agent_controlled decorated methods
   6. Auto-derives ``cell_ids`` from ``read_measurements`` and ``control_functions`` keys
   7. Auto-initializes ``send_commands`` as an empty ``deque``
   8. Initializes ``agent_requests`` queue and ``_agent_handlers`` map

   Example::

       @aic_app(name="MyNetworkApp")
       class MyNetworkApp(AicApp):
           aic_app_id = 1
           control_loop_update_time = 2
           read_measurements = {3: ["gain"]}
           control_functions = {3: ["SET_GAIN"]}
           # cell_ids and send_commands are auto-generated

           @classmethod
           def process(cls, measurements):
               pass

@command_validator Decorator
----------------------------

.. py:decorator:: ai_nn_controller.decorators.command_validator.command_validator(command_name)

   Decorator to register a validator function for a specific command.

   Command validators are **optional**. If no validator is defined for a command,
   it passes through unchanged. Validators are primarily useful when the FastAPI
   REST API or MCP tools are used to send manual control commands.

   :param command_name: Name of the command to validate (e.g., "SET_GAIN")

   The validator function should be a classmethod that takes a ``params`` dict
   and returns a tuple of ``(is_valid: bool, error_message: str | None)``.

   Example::

       from ai_nn_controller.decorators.command_validator import command_validator

       @aic_app(name="SafeApp")
       class SafeApp(AicApp):
           control_functions = {8: ["SET_GAIN"]}
           MAX_GAIN = 25.0

           # IMPORTANT: @classmethod must be ABOVE @command_validator
           @classmethod
           @command_validator("SET_GAIN")
           def validate_set_gain(cls, params: dict) -> tuple[bool, str | None]:
               """Validate SET_GAIN commands."""
               target_gain = params.get("target_gain", 0)
               if target_gain > cls.MAX_GAIN:
                   return False, f"Gain {target_gain} exceeds max {cls.MAX_GAIN}"
               return True, None

   **Validator Parameters:**

   The ``params`` dict contains:

   - ``node_id``: Target node ID
   - Command-specific parameters (e.g., ``target_gain``, ``amp_type``)

   **Validator Return Values:**

   - ``(True, None)``: Command is valid, proceed with execution
   - ``(False, "error message")``: Command is rejected with error

   **Behavior:**

   - No validator defined: Command passes through unchanged
   - Validator raises exception: Command is rejected for safety
   - Applied to both REST API/MCP calls and internal ``add_command()`` calls

@agent_controlled Decorator
----------------------------

.. py:decorator:: ai_nn_controller.decorators.agent_controlled.agent_controlled(name, description, schema)

   Decorator to register a method as an agent-controlled operation.

   Agent-controlled operations allow MCP/AI agents to execute logic **inside the
   process loop**, with access to live measurements and the app's internal state.
   Unlike regular MCP control tools (which bypass ``process()``), these handlers
   are synchronized with the process cycle.

   :param name: Operation name (used as MCP tool suffix, e.g., "optimize_gain")
   :param description: Human-readable description for the MCP tool
   :param schema: JSON Schema for the tool's input parameters (properties + required)

   The handler function should be a classmethod that takes ``request`` (dict of
   MCP arguments) and ``measurements`` (dict from the process loop) and returns
   a result dict.

   Example::

       from ai_nn_controller.decorators.agent_controlled import agent_controlled

       @aic_app(name="SmartApp")
       class SmartApp(AicApp):
           read_measurements = {8: ["preamp_gain"]}
           control_functions = {8: ["SET_GAIN"]}

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
               """Runs inside the process loop."""
               node_id = request["node_id"]
               latest = measurements.get(node_id, [{}])[-1] or {}
               new_gain = latest.get("preamp_gain", 15) + 2.0
               cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"target_gain": new_gain}}))
               return {"status": "applied", "new_gain": new_gain}

   **Handler Parameters:**

   - ``request`` (dict): The MCP tool arguments matching the defined schema
   - ``measurements`` (dict): Current measurements from the process loop

   **Handler Return Value:**

   - A ``dict`` that is returned to the MCP caller as the tool result

   **Synchronization:**

   - The MCP handler waits (non-blocking) for the process loop to execute the handler
   - Timeout defaults to ``control_loop_update_time * 3 + 5`` seconds
   - The app must be in ``running`` state for agent-controlled tools to work

AicManager
----------

.. py:class:: ai_nn_controller.managers.AicManager

   Centralized manager for AIC applications (singleton pattern).

   **Class Attributes:**

   .. py:attribute:: aic_apps
      :type: dict

      Registry of all applications keyed by name.

   .. py:attribute:: routers
      :type: dict

      FastAPI routers for each application.

   .. py:attribute:: controller_instance
      :type: AicController

      Reference to the active controller.

   **Methods:**

   .. py:method:: add_aic_app(name, aic_app)
      :classmethod:

      Register an application. Called by @aic_app decorator.

   .. py:method:: add_router(name, router)
      :classmethod:

      Register a FastAPI router for an application.

   .. py:method:: get_routers()
      :classmethod:

      Get all registered routers.

   .. py:method:: set_controller(controller)
      :classmethod:

      Set the controller instance.

   .. py:method:: update_state(app_name, state)
      :classmethod:

      Update application state via controller.

   .. py:method:: get_app_state(app_name)
      :classmethod:

      Get application state.

   .. py:method:: get_measurements(app_name)
      :classmethod:

      Get latest measurements.

   .. py:method:: send_manual_control(app_name, node_id, command)
      :classmethod:

      Send manual control command.

Command Registry
----------------

.. py:function:: ai_nn_controller.registry.register_command(name, handler, schema=None)

   Register a command with the framework.

   :param name: Unique command name (e.g., "SET_GAIN")
   :param handler: Function taking (node_id, value) returning JSON string
   :param schema: Optional JSON Schema for MCP tool generation

   Example::

       register_command(
           name="SET_GAIN",
           handler=lambda node_id, value: json.dumps({"gain": value["target"]}),
           schema={"description": "Set gain", "properties": {...}}
       )

.. py:function:: ai_nn_controller.registry.register_commands(commands)

   Register multiple commands at once.

   :param commands: Dict mapping names to {"handler": fn, "schema": dict}

.. py:function:: ai_nn_controller.registry.execute_command(name, node_id, value)

   Execute a registered command.

   :param name: Command name
   :param node_id: Target node ID
   :param value: Command parameters
   :returns: JSON string payload
   :raises ValueError: If command not registered

.. py:function:: ai_nn_controller.registry.has_command(name)

   Check if a command is registered.

   :param name: Command name
   :returns: True if command exists

.. py:function:: ai_nn_controller.registry.list_commands()

   List all registered command names.

   :returns: List of command names

.. py:function:: ai_nn_controller.registry.get_command_schema(name, allowed_node_ids=None)

   Get JSON schema for a command.

   :param name: Command name
   :param allowed_node_ids: Optional list to constrain node_id enum
   :returns: JSON Schema dict

MeasurementsHandler
-------------------

.. py:class:: ai_nn_controller.enums.MeasurementsHandler

   Enumeration for special measurement handling.

   .. py:attribute:: ALL_MEASUREMENTS

      Include all available measurements from a node.

   Example::

       read_measurements = {
           3: [MeasurementsHandler.ALL_MEASUREMENTS]
       }

Configuration
-------------

.. py:function:: ai_nn_controller.config.vprint(*args, **kwargs)

   Verbose print function. Only outputs when verbose mode is enabled.

.. py:class:: ai_nn_controller.config.AicConfig

   Global configuration settings.

   .. py:method:: set_verbose(enabled)
      :classmethod:

      Enable or disable verbose logging.

Related Subpackages
--------------------

The framework ships several smaller subpackages that back features described
elsewhere in these docs. They're listed here as an index rather than
documented in full, since each is small and already covered in context:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Subpackage
     - Purpose
   * - ``ai_nn_controller.protocol``
     - ``MessageEnvelope`` — the wire format used for every measurement and command sent over ZeroMQ (schema, version, correlation/lineage/idempotency IDs, payload). See :doc:`../user_guide/architecture` and :doc:`broker`.
   * - ``ai_nn_controller.safety``
     - ``SafetyPolicyEngine`` — a global command blocklist enforced on every manual and app-issued command before it is sent. See :doc:`../examples/conflict_mitigation`.
   * - ``ai_nn_controller.arbitration``
     - ``CommandArbitrator`` — resolves duplicate/conflicting commands to the same node using a configurable strategy (``last_write_wins`` or ``min_gap``, set via ``AIC_ARBITRATION_STRATEGY``). See :doc:`../examples/conflict_mitigation`.
   * - ``ai_nn_controller.observability``
     - ``structured_log`` — emits JSON-formatted log lines for key lifecycle events (measurement ingress, command egress, queue backpressure, agent request draining).
   * - ``ai_nn_controller.plugin_framework``
     - Runtime service plugins (``AicPlugin``, ``required_plugins``). See :doc:`plugin_framework`.
   * - ``ai_nn_controller.plugins``
     - Capability-discovery registry and the control-application entry-point loader. See :doc:`plugins`.
