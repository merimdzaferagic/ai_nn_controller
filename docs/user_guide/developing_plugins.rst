Developing Plugins
====================

This guide covers how to develop **plugins** for **ai_nn_controller** using the
``plugin_framework`` module.

A plugin gives control applications a typed, reusable interface to an
external service — a time-series database, an ML model registry, a
monitoring backend, or anything else multiple apps might need to talk to.
Instead of every control application reimplementing its own InfluxDB or
MLflow client, a plugin implements that integration once and is declared as a
dependency by any app that needs it.

When to Write a Plugin
-----------------------

Write a plugin when you have logic that:

- Talks to an external service shared by multiple control applications
  (a database, a metrics backend, a model store)
- Should be swappable independently of any single app (e.g. a "storage"
  plugin backed by InfluxDB today, something else tomorrow)
- Benefits from a single, well-defined lifecycle (``connect()`` /
  ``disconnect()`` / health checks) managed by the controller

If your logic is specific to one control application, keep it in that app's
``aic_app.py`` instead — a plugin is for behaviour shared across apps.

Core Components
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Description
   * - ``AicPlugin``
     - Base class for all plugins. Subclass this and implement ``connect()``/``disconnect()`` plus your own public methods.
   * - ``StoragePlugin`` / ``ModelRegistryPlugin`` / ``MonitoringPlugin``
     - Optional typed mixins that define a conventional method surface for common plugin categories.
   * - ``@aic_plugin(name="...", plugin_type="...")``
     - Decorator that registers a plugin class with ``PluginManager``.
   * - ``PluginManager``
     - Runtime registry of loaded plugins, populated by ``@aic_plugin``.

Import everything from the package:

.. code-block:: python

   from ai_nn_controller.plugin_framework import AicPlugin, aic_plugin

AicPlugin Base Class
----------------------

Every plugin subclasses ``AicPlugin`` and implements its lifecycle hooks:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``connect()``
     - **Optional but recommended.** Initialise the connection to the external service. Called once by ``AicController`` at startup, after all plugins and apps have loaded.
   * - ``disconnect()``
     - **Optional.** Release resources. Called at controller shutdown.
   * - ``is_healthy()``
     - **Optional.** Return ``True``/``False``. Defaults to always ``True``.

All plugin methods are ``classmethod`` s — plugins are used as class-level
singletons, the same way control applications are.

Typed Mixins
~~~~~~~~~~~~

If your plugin fits one of these categories, subclass the mixin instead of
``AicPlugin`` directly — it documents intent and gives a predictable method
surface for consumers:

.. code-block:: python

   from ai_nn_controller.plugin_framework import StoragePlugin, aic_plugin

   @aic_plugin(name="InfluxStorage", plugin_type="storage")
   class InfluxStorage(StoragePlugin):
       @classmethod
       def connect(cls):
           cls._client = make_influx_client(...)

       @classmethod
       def write(cls, key, value, tags=None):
           cls._client.write(key, value, tags or {})

       @classmethod
       def read(cls, query):
           return cls._client.query(query)

``StoragePlugin`` (``write``/``read``), ``ModelRegistryPlugin``
(``load_model``/``save_model``), and ``MonitoringPlugin``
(``push_metric``/``get_metric``) are available. A plugin that doesn't fit any
of these — like the reference ``ConsolePlugin`` below — can subclass
``AicPlugin`` directly and expose whatever methods make sense.

The @aic_plugin Decorator
---------------------------

.. code-block:: python

   @aic_plugin(name="ConsolePlugin", plugin_type="generic")
   class ConsolePlugin(AicPlugin):
       @classmethod
       def connect(cls):
           print("[ConsolePlugin] connected")

- ``name`` is the string control apps use in ``required_plugins`` and to look
  the plugin up via ``cls.plugins["ConsolePlugin"]``. It must be unique —
  registering a second plugin under the same name raises ``RuntimeError``.
- ``plugin_type`` is a free-form category string (``"storage"``,
  ``"model_registry"``, ``"monitoring"``, or ``"generic"``).

Worked Reference: console_plugin
-----------------------------------

The repository ships ``plugins/console_plugin/`` as the minimal reference
implementation — a plugin with no external dependencies that prints
structured messages to stdout instead of calling a real service. Use it as
the template for a new plugin's file layout.

``plugins/console_plugin/aic_plugin.py``:

.. code-block:: python

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

Declaring the Entry Point
----------------------------

Plugins ship as independent, installable Python packages. The controller
discovers them at startup via the ``ai_nn_controller.plugin_init`` entry-point
group — the same mechanism used to discover control applications
(``ai_nn_controller.app_init``, see :doc:`developing_apps`).

``plugins/console_plugin/pyproject.toml``:

.. code-block:: toml

   [build-system]
   requires = ["setuptools>=61.0", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "console-plugin"
   version = "0.1.0"
   description = "Console logging plugin for ai_nn_controller"
   requires-python = ">=3.9"
   dependencies = ["ai_nn_controller>=1.0.0"]

   [project.entry-points."ai_nn_controller.plugin_init"]
   "console_plugin:aic_plugin" = "ai_nn_controller.plugin_framework.entrypoints:bootstrap_plugin_bundle"

   [tool.setuptools]
   py-modules = ["aic_plugin"]

The entry-point name (``"console_plugin:aic_plugin"``) is parsed as
``"bundle_name:plugin_module"`` — ``bootstrap_plugin_bundle`` imports
``plugin_module`` (default ``"aic_plugin"``), which triggers the
``@aic_plugin`` decorator and registers the class with ``PluginManager``.

Declaring a Plugin Dependency in a Control App
-------------------------------------------------

A control application declares which plugins it needs via
``required_plugins``, then accesses them through ``cls.plugins``:

.. code-block:: python

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp

   @aic_app(name="MyApp")
   class MyApp(AicApp):
       required_plugins = ["ConsolePlugin"]
       read_measurements = {3: ["gain", "power"]}
       control_functions = {}

       @classmethod
       def process(cls, measurements):
           console = cls.plugins["ConsolePlugin"]
           latest = measurements.get(3, [{}])[-1]
           console.log_measurement(3, latest)
           console.log_event("process_tick", app="MyApp")

If ``ConsolePlugin`` isn't installed (or wasn't loaded via an entry point),
``AicController`` raises ``RuntimeError`` at startup listing the missing
plugin and whatever *is* available — the app never starts with a silently
missing dependency. See :doc:`developing_apps` for the full app-development
guide.

Installation Order
--------------------

Plugins run **inside** the control application's process — they are not
separate containers. A control app's Dockerfile must install packages in
this order:

1. The ``ai_nn_controller`` framework
2. Every plugin the app requires
3. The control application itself

.. code-block:: dockerfile

   FROM python:3.9-slim

   # 1. Framework
   COPY controller_components/ai_nn_controller/ /tmp/ai_nn_controller/
   RUN pip install --no-cache-dir /tmp/ai_nn_controller

   # 2. Plugins
   COPY plugins/console_plugin/ /tmp/console_plugin/
   RUN pip install --no-cache-dir /tmp/console_plugin

   # 3. The app itself (triggers the ai_nn_controller.app_init entry point)
   COPY control_applications/my_app/ /app_pkg/
   RUN pip install --no-cache-dir /app_pkg

   WORKDIR /app
   COPY control_applications/my_app/ ./
   CMD ["python3", "aic_app.py"]

In ``docker-compose.yml``, mount the plugin source alongside the framework
and app so it can be installed at container start (matching the pattern used
for the framework itself):

.. code-block:: yaml

   aic_server:
     build:
       context: ./
       dockerfile: control_applications/my_app/Dockerfile
     volumes:
       - ./control_applications/my_app/:/app
       - ./controller_components/ai_nn_controller/:/ai_nn_controller
       - ./plugins/console_plugin/:/console_plugin
     command: >
       sh -c "pip install --no-cache-dir /ai_nn_controller
       && pip install --no-cache-dir /console_plugin
       && pip install --no-cache-dir /app
       && python3 aic_app.py --verbose"

If a plugin also runs its own external service (e.g. an MLflow server or
InfluxDB), add a dedicated compose service for it and point the plugin's
``connect()`` at that service via environment variables — the plugin package
itself still installs into the app's container, only the backend it talks to
is a separate service.

Best Practices
---------------

1. **Keep ``connect()`` idempotent**: it may run once at controller startup; don't assume it's the only time it runs.
2. **Fail loudly on missing config**: if a plugin needs credentials or a URL, raise a clear error from ``connect()`` rather than silently degrading.
3. **Use a typed mixin when one fits**: ``StoragePlugin``/``ModelRegistryPlugin``/``MonitoringPlugin`` give consumers a predictable API.
4. **One plugin, one external system**: don't bundle unrelated integrations into a single plugin class.
5. **Version your plugin package**: plugins are installed as independent packages (e.g. ``console-plugin>=0.1.0``) with their own version history.

Next Steps
-----------

- :doc:`../api/plugin_framework` — full API reference for ``AicPlugin``, ``PluginManager``, and entry-point loading
- :doc:`../api/plugins` — the capability-discovery registry and app entry-point loader
- :doc:`developing_apps` — declaring ``required_plugins`` on a control application
- :doc:`../examples/plugin_example` — a complete worked example
