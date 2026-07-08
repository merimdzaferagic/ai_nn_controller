Plugin Framework API (ai_nn_controller.plugin_framework)
==========================================================

This is the API reference for ``ai_nn_controller.plugin_framework`` — the
runtime plugin system. Plugins are independent Python packages that give
control applications a typed, reusable interface to external services
(time-series databases, ML model registries, monitoring backends, and so on).

.. note::

   ``plugin_framework`` (this page) is distinct from :doc:`plugins`, which is
   a separate subpackage for capability-discovery metadata and the
   control-application entry-point loader. See :doc:`plugins` for that API.

AicPlugin
---------

.. py:class:: ai_nn_controller.plugin_framework.AicPlugin

   Base class for all AIC plugins.

   .. py:attribute:: plugin_type
      :type: str

      Category string. Default: ``"generic"``.

   .. py:attribute:: u_name
      :type: str

      Unique plugin name, set by the ``@aic_plugin`` decorator.

   **Methods:**

   .. py:method:: connect()
      :classmethod:

      Initialise the connection to the external service. Called once by
      ``AicController`` at controller startup, after all plugins and apps
      have been loaded.

   .. py:method:: disconnect()
      :classmethod:

      Release resources. Called by ``AicController`` at shutdown.

   .. py:method:: is_healthy()
      :classmethod:

      Return ``True`` if the plugin is operational. Default implementation
      always returns ``True`` — override for real health checks.

Typed Plugin Mixins
--------------------

These optional base classes define a conventional method surface for common
plugin categories. Using them is not required — any ``AicPlugin`` subclass
works — but they make a plugin's intent explicit and give consumers a
predictable API to call.

.. py:class:: ai_nn_controller.plugin_framework.StoragePlugin

   Mixin for plugins that store and retrieve time-series or structured data
   (e.g. InfluxDB). Sets ``plugin_type = "storage"``.

   .. py:method:: write(key, value, tags=None)
      :classmethod:

      :param key: Series or record key
      :param value: Value to store
      :param tags: Optional dict of tags/labels

   .. py:method:: read(query)
      :classmethod:

      :param query: Backend-specific query string
      :returns: List of matching records

.. py:class:: ai_nn_controller.plugin_framework.ModelRegistryPlugin

   Mixin for plugins that manage ML model versioning (e.g. MLflow). Sets
   ``plugin_type = "model_registry"``.

   .. py:method:: load_model(name, version=None)
      :classmethod:

      :param name: Model name
      :param version: Optional specific version; latest if omitted

   .. py:method:: save_model(name, model, metrics=None)
      :classmethod:

      :param name: Model name
      :param model: Model object to persist
      :param metrics: Optional dict of metrics to log alongside the model

.. py:class:: ai_nn_controller.plugin_framework.MonitoringPlugin

   Mixin for plugins that push or pull observability metrics (e.g.
   Prometheus). Sets ``plugin_type = "monitoring"``.

   .. py:method:: push_metric(name, value, labels=None)
      :classmethod:

      :param name: Metric name
      :param value: Metric value
      :param labels: Optional dict of labels

   .. py:method:: get_metric(name, labels=None)
      :classmethod:

      :param name: Metric name
      :param labels: Optional dict of labels to filter by
      :returns: Metric value

@aic_plugin Decorator
----------------------

.. py:decorator:: ai_nn_controller.plugin_framework.aic_plugin(name, plugin_type="generic")

   Decorator that registers an ``AicPlugin`` subclass with ``PluginManager``.

   :param name: Unique plugin name. This is the string control apps use in
      ``required_plugins`` and to look the plugin up via ``cls.plugins[name]``.
   :param plugin_type: Category string — ``"storage"``, ``"model_registry"``,
      ``"monitoring"``, or ``"generic"`` (default).

   :raises RuntimeError: If a plugin with the same ``name`` is already registered.

   Example::

       from ai_nn_controller.plugin_framework import AicPlugin, aic_plugin

       @aic_plugin(name="ConsolePlugin", plugin_type="generic")
       class ConsolePlugin(AicPlugin):
           @classmethod
           def connect(cls):
               print("[ConsolePlugin] connected")

           @classmethod
           def log(cls, message: str, level: str = "INFO") -> None:
               print(f"[{level}] {message}")

PluginManager
-------------

.. py:class:: ai_nn_controller.plugin_framework.PluginManager

   Runtime registry of loaded plugin classes, populated by the ``@aic_plugin``
   decorator. Analogous to ``AicManager`` for control applications.

   **Methods:**

   .. py:method:: register(name, plugin_class)
      :classmethod:

      Register a plugin class under ``name``. Called by ``@aic_plugin``.

      :raises RuntimeError: If ``name`` is already registered.

   .. py:method:: get(name)
      :classmethod:

      :param name: Plugin name
      :returns: The registered plugin class, or ``None`` if not found

   .. py:method:: has(name)
      :classmethod:

      :param name: Plugin name
      :returns: ``True`` if a plugin with that name is registered

   .. py:method:: list_plugins(plugin_type=None)
      :classmethod:

      :param plugin_type: Optional category filter
      :returns: List of registered plugin names

   .. py:method:: all_plugins()
      :classmethod:

      :returns: Dict mapping every registered plugin name to its class

Entry-Point Loading
--------------------

Plugins ship as independent Python packages and are discovered at controller
startup via Python entry points, the same mechanism used for control
applications (see :doc:`plugins`).

.. py:data:: ai_nn_controller.plugin_framework.PLUGIN_ENTRYPOINT_GROUP

   The entry-point group name: ``"ai_nn_controller.plugin_init"``.

.. py:function:: ai_nn_controller.plugin_framework.load_plugin_entrypoints(group="ai_nn_controller.plugin_init")

   Discover and execute every hook registered under ``group``. Idempotent —
   safe to call more than once; only runs once per process. Called by
   ``AicController.__init__`` before ``load_app_entrypoints()`` so that
   ``required_plugins`` can be validated before any app starts.

.. py:function:: ai_nn_controller.plugin_framework.bootstrap_plugin_bundle(ep=None)

   The default entry-point hook used by plugin packages. Parses the
   entry-point name as ``"bundle_name:plugin_module"`` (``plugin_module``
   defaults to ``"aic_plugin"``) and imports that module, which triggers the
   ``@aic_plugin`` decorator to run and register the plugin class.

   A plugin package declares this in its ``pyproject.toml``::

       [project.entry-points."ai_nn_controller.plugin_init"]
       "my_plugin:aic_plugin" = "ai_nn_controller.plugin_framework.entrypoints:bootstrap_plugin_bundle"

Validation
----------

.. py:function:: ai_nn_controller.plugin_framework.validate_app_plugins(app_class)

   Check that every plugin name listed in ``app_class.required_plugins`` is
   registered in ``PluginManager``. Called by ``AicController`` for each app,
   after all plugin and app entry points have loaded but before the app
   starts processing.

   :param app_class: An ``AicApp`` subclass
   :raises RuntimeError: Listing any missing plugin names and the plugins
      that *are* available, if ``required_plugins`` names anything not
      registered.

See Also
--------

- :doc:`plugins` — capability-discovery registry and the control-application
  entry-point loader
- :doc:`../user_guide/developing_plugins` — step-by-step guide to writing a plugin
- :doc:`../examples/plugin_example` — full worked example using ``ConsolePlugin``
