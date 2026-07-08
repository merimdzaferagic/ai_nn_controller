Plugin Example
================

This example shows how to write a plugin, declare it as a dependency from a
control application, and wire the two together in Docker.

The Plugin
----------

``plugins/console_plugin/aic_plugin.py`` is the repository's reference
plugin implementation — it has no external dependencies and simply prints
structured messages to stdout, which makes it useful both as documentation
and as a smoke test for the plugin loading mechanism.

.. code-block:: python

   """
   ConsolePlugin — a dummy plugin that prints to stdout.

   This is the reference implementation showing the minimum required structure
   for an ai_nn_controller plugin. Real plugins would replace the print calls
   with SDK calls to InfluxDB, MLflow, Prometheus, etc.
   """

   import datetime

   from ai_nn_controller.plugin_framework import AicPlugin, aic_plugin


   @aic_plugin(name="ConsolePlugin", plugin_type="generic")
   class ConsolePlugin(AicPlugin):
       """Prints structured messages to stdout. No external dependencies."""

       _prefix: str = "[ConsolePlugin]"

       @classmethod
       def connect(cls) -> None:
           cls._print("INFO", "connected")

       @classmethod
       def disconnect(cls) -> None:
           cls._print("INFO", "disconnected")

       @classmethod
       def is_healthy(cls) -> bool:
           return True

       @classmethod
       def log(cls, message: str, level: str = "INFO") -> None:
           """Print a free-form message."""
           cls._print(level, message)

       @classmethod
       def log_measurement(cls, node_id: int, data: dict) -> None:
           """Print the latest measurement snapshot for a node."""
           cls._print("DATA", f"node={node_id} {data}")

       @classmethod
       def log_command(cls, command: str, payload: dict) -> None:
           """Print a command that is about to be (or was) sent."""
           cls._print("CMD", f"{command} payload={payload}")

       @classmethod
       def log_event(cls, event: str, **kwargs) -> None:
           """Print a named event with arbitrary keyword metadata."""
           extras = " ".join(f"{k}={v}" for k, v in kwargs.items())
           cls._print("EVENT", f"{event} {extras}".strip())

       @classmethod
       def _print(cls, level: str, message: str) -> None:
           ts = datetime.datetime.now().isoformat(timespec="seconds")
           print(f"{ts} {cls._prefix} [{level}] {message}")

Its entry point is declared in ``plugins/console_plugin/pyproject.toml``:

.. code-block:: toml

   [project.entry-points."ai_nn_controller.plugin_init"]
   "console_plugin:aic_plugin" = "ai_nn_controller.plugin_framework.entrypoints:bootstrap_plugin_bundle"

The App That Uses It
----------------------

.. code-block:: python

   """
   plugin_demo.py - A control application that depends on ConsolePlugin
   """

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController

   @aic_app(name="PluginDemo")
   class PluginDemo(AicApp):
       """Monitors node 3 and logs every measurement via ConsolePlugin."""

       aic_app_id = 100
       control_loop_update_time = 2

       # Declares a hard dependency on the ConsolePlugin plugin
       required_plugins = ["ConsolePlugin"]

       read_measurements = {
           3: ["amp1_target_gain", "amp1_gain_tilt"]
       }
       control_functions = {}

       @classmethod
       def process(cls, measurements):
           console = cls.plugins["ConsolePlugin"]

           latest = measurements.get(3, [{}])[-1]
           if not latest:
               return

           console.log_measurement(3, latest)
           console.log_event("process_tick", app="PluginDemo")

   if __name__ == "__main__":
       AicController(with_api=True, api_port=8000, verbose=True).run()

Because ``required_plugins = ["ConsolePlugin"]`` is set, ``AicController``
checks at startup that a plugin named ``ConsolePlugin`` was registered by an
entry point. If ``console-plugin`` isn't installed in the app's container,
startup fails fast with::

    RuntimeError: App 'PluginDemo' requires plugins ['ConsolePlugin'] which
    are not registered. Available plugins: (none)

Docker: Install Order
------------------------

Plugins run inside the control application's own container/process — install
the framework, then the plugin, then the app itself:

.. code-block:: dockerfile

   FROM python:3.9-slim

   # 1. Framework
   COPY controller_components/ai_nn_controller/ /tmp/ai_nn_controller/
   RUN pip install --no-cache-dir /tmp/ai_nn_controller

   # 2. Plugin
   COPY plugins/console_plugin/ /tmp/console_plugin/
   RUN pip install --no-cache-dir /tmp/console_plugin

   # 3. App
   WORKDIR /app
   COPY control_applications/plugin_demo/ ./
   RUN pip install --no-cache-dir .

   CMD ["python3", "aic_app.py", "--verbose"]

The real ``control_applications/control_application_v2_example`` ships
exactly this pattern today — its ``NetworkApp1`` declares
``required_plugins = ["ConsolePlugin"]``, and the repo-root
``docker-compose.yml`` installs the framework, then
``plugins/console_plugin/``, then the app, in that order, inside the
``aic_server`` service.

Running the Example
---------------------

1. Make sure the infrastructure and the amp1 node are running:

   .. code-block:: bash

      docker compose up -d redis aic_register node_msg_broker amp1_node

2. Run the application locally (with the framework and ``console-plugin``
   both installed in your environment):

   .. code-block:: bash

      python plugin_demo.py --verbose

3. Start the app via the API:

   .. code-block:: bash

      curl -X PUT http://localhost:8000/apps/PluginDemo/state \
        -H "Content-Type: application/json" \
        -d '{"state": "running"}'

Expected Output
-----------------

.. code-block:: text

   2026-07-08T12:00:00 [ConsolePlugin] [INFO] connected
   2026-07-08T12:00:02 [ConsolePlugin] [DATA] node=3 {'amp1_target_gain': 20.5, 'amp1_gain_tilt': 1.2}
   2026-07-08T12:00:02 [ConsolePlugin] [EVENT] process_tick app=PluginDemo
   2026-07-08T12:00:04 [ConsolePlugin] [DATA] node=3 {'amp1_target_gain': 21.1, 'amp1_gain_tilt': 0.8}
   2026-07-08T12:00:04 [ConsolePlugin] [EVENT] process_tick app=PluginDemo

Key Concepts Demonstrated
----------------------------

1. **``@aic_plugin`` decorator**: registers a plugin class with ``PluginManager``
2. **``required_plugins``**: declares a hard dependency from an app onto a plugin
3. **``cls.plugins[name]``**: how a running app accesses a loaded plugin's methods
4. **Fail-fast validation**: the controller refuses to start an app whose plugin dependency is missing
5. **Install ordering**: framework → plugins → app, both in Dockerfiles and compose

Next Steps
-----------

- :doc:`../user_guide/developing_plugins` — full guide to writing your own plugin
- :doc:`../api/plugin_framework` — API reference for ``AicPlugin``, ``PluginManager``, entry points
- :doc:`../api/plugins` — capability-discovery registry
- :doc:`conflict_mitigation` — the real shipped example app that combines this plugin pattern with multi-app conflict arbitration
