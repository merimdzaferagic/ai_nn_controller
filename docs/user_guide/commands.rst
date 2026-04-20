Defining Commands
=================

Commands allow your applications to send control instructions to any type of
network node — optical, wireless, RAN, core network, and more. This guide covers
how to define and register custom commands.

Command System Overview
-----------------------

ai_nn_controller uses a registry-based command system:

1. **Define** a handler function that creates the command payload
2. **Register** the command with a name and optional schema
3. **Use** the command in your application via ``add_command()``

Commands registered with schemas automatically become MCP tools.

Defining a Command
------------------

Create a ``commands.py`` file in your application directory:

.. code-block:: python

   import json
   from ai_nn_controller.registry import register_command

   def set_gain_handler(node_id: int, value: dict) -> str:
       """
       Handler for SET_GAIN command.

       Args:
           node_id: Target node ID
           value: Command parameters

       Returns:
           JSON string payload for the node
       """
       return json.dumps({
           "command": "SET_GAIN",
           "amp_type": value.get("amp_type", "line"),
           "target_gain": value.get("target_gain", 0)
       })

   # Define the schema for MCP tool generation
   SET_GAIN_SCHEMA = {
       "description": "Set the target gain for an amplifier",
       "properties": {
           "node_id": {
               "type": "integer",
               "description": "Target node ID"
           },
           "amp_type": {
               "type": "string",
               "enum": ["line", "preamp", "booster"],
               "description": "Type of amplifier to control"
           },
           "target_gain": {
               "type": "number",
               "description": "Target gain value in dB"
           }
       },
       "required": ["node_id", "target_gain"]
   }

   # Register the command
   register_command(
       name="SET_GAIN",
       handler=set_gain_handler,
       schema=SET_GAIN_SCHEMA
   )

Command Components
------------------

Handler Function
~~~~~~~~~~~~~~~~

The handler transforms high-level parameters into node-specific payloads:

.. code-block:: python

   def my_handler(node_id: int, value: dict) -> str:
       """
       Args:
           node_id: Target node ID (passed automatically)
           value: Parameters from add_command() call

       Returns:
           JSON string that will be sent to the node
       """
       # Build node-specific payload
       payload = {
           "my_param": value.get("param1"),
           "another": value.get("param2", "default")
       }
       return json.dumps(payload)

Schema Definition
~~~~~~~~~~~~~~~~~

Schemas enable:

- MCP tool generation with proper input validation
- API documentation
- Client-side validation

.. code-block:: python

   MY_COMMAND_SCHEMA = {
       "description": "Human-readable description for the MCP tool",
       "properties": {
           "node_id": {
               "type": "integer",
               "description": "Target node ID"
           },
           "param1": {
               "type": "number",
               "description": "First parameter"
           },
           "param2": {
               "type": "string",
               "enum": ["option1", "option2"],
               "description": "Second parameter with fixed options"
           }
       },
       "required": ["node_id", "param1"]
   }

Registering Commands
--------------------

Single Command
~~~~~~~~~~~~~~

.. code-block:: python

   register_command(
       name="MY_COMMAND",
       handler=my_handler,
       schema=MY_COMMAND_SCHEMA  # Optional - uses default if not provided
   )

Multiple Commands
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from ai_nn_controller.registry import register_commands

   register_commands({
       "SET_GAIN": {
           "handler": set_gain_handler,
           "schema": SET_GAIN_SCHEMA
       },
       "SET_VOA": {
           "handler": set_voa_handler,
           "schema": SET_VOA_SCHEMA
       },
       "SET_TILT": {
           "handler": set_tilt_handler
           # No schema - will auto-generate default
       }
   })

Using Commands in Applications
------------------------------

Import Commands
~~~~~~~~~~~~~~~

Import your commands module at the top of your app file:

.. code-block:: python

   # This imports and registers all commands when the module loads
   import commands

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp

   @aic_app(name="MyApp")
   class MyApp(AicApp):
       # ...

Declare Control Functions
~~~~~~~~~~~~~~~~~~~~~~~~~

Specify which commands each node supports:

.. code-block:: python

   control_functions = {
       3: ["SET_GAIN"],           # Node 3 supports SET_GAIN
       8: ["SET_GAIN", "SET_VOA", "SET_TILT"]  # Node 8 supports all three
   }

Send Commands
~~~~~~~~~~~~~

Use ``add_command()`` in your ``process()`` method:

.. code-block:: python

   @classmethod
   def process(cls, measurements):
       # Send a command
       cls.add_command((
           "SET_GAIN",  # Command name
           {
               "node_id": 8,        # Target node
               "value": {           # Parameters for handler
                   "amp_type": "preamp",
                   "target_gain": 20.0
               }
           }
       ))

Complete Example
----------------

``commands.py``:

.. code-block:: python

   import json
   from ai_nn_controller.registry import register_command

   # SET_GAIN command
   def set_gain_handler(node_id: int, value: dict) -> str:
       return json.dumps({
           "command": "SET_GAIN",
           "amp_type": value.get("amp_type", "line"),
           "target_gain": value.get("target_gain", 0)
       })

   SET_GAIN_SCHEMA = {
       "description": "Set amplifier target gain",
       "properties": {
           "node_id": {"type": "integer", "description": "Target node"},
           "amp_type": {"type": "string", "enum": ["line", "preamp", "booster"]},
           "target_gain": {"type": "number", "description": "Gain in dB"}
       },
       "required": ["node_id", "target_gain"]
   }

   # SET_VOA command
   def set_voa_handler(node_id: int, value: dict) -> str:
       return json.dumps({
           "command": "SET_VOA",
           "attenuation": value.get("attenuation", 0)
       })

   SET_VOA_SCHEMA = {
       "description": "Set Variable Optical Attenuator",
       "properties": {
           "node_id": {"type": "integer", "description": "Target node"},
           "attenuation": {"type": "number", "description": "Attenuation in dB"}
       },
       "required": ["node_id", "attenuation"]
   }

   # Register all commands
   register_command("SET_GAIN", set_gain_handler, SET_GAIN_SCHEMA)
   register_command("SET_VOA", set_voa_handler, SET_VOA_SCHEMA)

``aic_app.py``:

.. code-block:: python

   import commands  # Register commands

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController

   @aic_app(name="ControllerApp")
   class ControllerApp(AicApp):
       read_measurements = {8: ["preamp_gain", "voa_attenuation"]}
       control_functions = {8: ["SET_GAIN", "SET_VOA"]}
       # cell_ids and send_commands are auto-generated by @aic_app

       @classmethod
       def process(cls, measurements):
           data = measurements.get(8, [{}])[-1]
           gain = data.get("preamp_gain", 0)

           if gain > 25:
               cls.add_command(("SET_GAIN", {
                   "node_id": 8,
                   "value": {"amp_type": "preamp", "target_gain": 20}
               }))

   if __name__ == "__main__":
       AicController(with_api=True).run()

Registry API Reference
----------------------

.. code-block:: python

   from ai_nn_controller.registry import (
       register_command,      # Register a single command
       register_commands,     # Register multiple commands
       has_command,           # Check if command exists
       execute_command,       # Execute a command
       list_commands,         # List all registered commands
       get_command_schema,    # Get schema for a command
       get_command_handler,   # Get handler function
       clear_registry         # Clear all commands (for testing)
   )

Default Schemas
---------------

If you don't provide a schema, a default is generated:

.. code-block:: python

   # Default schema for "MY_COMMAND"
   {
       "description": "Execute My Command command",
       "properties": {
           "node_id": {
               "type": "integer",
               "description": "The ID of the target node"
           },
           "payload": {
               "type": "object",
               "description": "Command parameters"
           }
       },
       "required": ["node_id"]
   }

Next Steps
----------

- :doc:`../api/mcp` - MCP integration details
- :doc:`../examples/basic_app` - Complete examples
