Capability Discovery API (ai_nn_controller.plugins)
======================================================

This is the API reference for ``ai_nn_controller.plugins`` — despite the
similar name, this subpackage is **not** the runtime plugin system (that's
:doc:`plugin_framework`). ``ai_nn_controller.plugins`` provides two
complementary things:

1. A generic **capability-discovery metadata registry** (``CapabilityMetadata`` /
   ``PluginRegistry``) used to catalogue the controller, every loaded app,
   every loaded runtime plugin, and every app bundle, so they can be
   introspected at runtime.
2. The **control-application entry-point loader** (``load_app_entrypoints`` /
   ``bootstrap_application_bundle``) — the mechanism that discovers and
   imports control application packages, analogous to how
   :doc:`plugin_framework`'s entry-point loader discovers runtime plugins.

Both are wired into ``AicController.__init__`` and are unrelated to whether a
given control app declares ``required_plugins``.

CapabilityMetadata
-------------------

.. py:class:: ai_nn_controller.plugins.CapabilityMetadata(name, plugin_type, schema="urn:ai-nnc:capability:1", version="1.0.0", compatibility=None, capabilities=None, extra=None)

   Dataclass describing one discoverable capability — an app, a runtime
   plugin, the controller itself, or an app bundle.

   :param name: Name of the capability being described
   :param plugin_type: Category — e.g. ``"controller"``, ``"app"``, ``"plugin"``, ``"app_bundle"``
   :param schema: Schema URN for this metadata format. Default: ``"urn:ai-nnc:capability:1"``
   :param version: Version string for this capability. Default: ``"1.0.0"``
   :param compatibility: A :py:class:`CompatibilityRange`; defaults to ``1.0.0``–``2.x``
   :param capabilities: List of capability strings (e.g. command names for an app bundle)
   :param extra: Free-form dict of additional metadata

   .. py:method:: to_dict()

      :returns: A plain ``dict`` representation, used for JSON responses from
         the capability-discovery API.

.. py:class:: ai_nn_controller.plugins.CompatibilityRange(min_version="1.0.0", max_version="2.x")

   Dataclass describing the version range a capability is compatible with.

PluginRegistry
--------------

.. py:class:: ai_nn_controller.plugins.PluginRegistry

   Class-level catalogue of registered ``CapabilityMetadata``, keyed
   internally by ``"{plugin_type}:{name}"``.

   **Methods:**

   .. py:method:: register(metadata)
      :classmethod:

      Register (or overwrite) a capability entry.

      :param metadata: A :py:class:`CapabilityMetadata` instance

   .. py:method:: discover(plugin_type=None)
      :classmethod:

      :param plugin_type: Optional category filter (e.g. ``"app"``, ``"plugin"``)
      :returns: List of ``dict`` (via ``to_dict()``) for every matching entry

   ``AicController`` populates this registry automatically: it registers
   itself (``plugin_type="controller"``), every loaded app
   (``plugin_type="app"``), every loaded runtime plugin
   (``plugin_type="plugin"``), and every app bundle discovered via entry
   points (``plugin_type="app_bundle"``). Call
   ``AicController.discover_capabilities()`` to retrieve the full catalogue
   at runtime.

Control-Application Entry-Point Loading
-----------------------------------------

Control applications ship as independent Python packages and are discovered
at controller startup the same way runtime plugins are (see
:doc:`plugin_framework`), but under a different entry-point group.

.. py:data:: ai_nn_controller.plugins.ENTRYPOINT_GROUP

   The entry-point group name: ``"ai_nn_controller.app_init"``.

.. py:function:: ai_nn_controller.plugins.load_app_entrypoints(group="ai_nn_controller.app_init")

   Discover and execute every hook registered under ``group``. Idempotent —
   safe to call more than once; only runs once per process. Called by
   ``AicController.__init__`` **after** ``load_plugin_entrypoints()``, so
   that runtime plugins are available before any app's ``required_plugins``
   is validated.

.. py:function:: ai_nn_controller.plugins.bootstrap_application_bundle(ep=None)

   The default entry-point hook used by control application packages. Parses
   the entry-point name as ``"bundle_name:app_module:commands_module"``
   (``app_module`` defaults to ``"aic_app"``, ``commands_module`` defaults to
   ``"commands"``) and:

   1. Imports the commands module and calls its ``register_specific_commands()``
      (if defined) to register commands with the framework's command registry.
   2. Calls the commands module's ``get_command_capabilities()`` (if defined)
      to collect capability strings for the registry entry.
   3. Imports the app module, which runs the ``@aic_app`` decorator on any
      application classes it defines. Guards against re-importing a module
      that is already running as ``__main__`` (i.e. when launched directly
      via ``python3 aic_app.py``).
   4. Registers a ``CapabilityMetadata(plugin_type="app_bundle", ...)`` entry
      in ``PluginRegistry`` describing the newly loaded app(s).

   A control application package declares this in its ``pyproject.toml``::

       [project.entry-points."ai_nn_controller.app_init"]
       "my_app:aic_app:commands" = "ai_nn_controller.plugins.entrypoints:bootstrap_application_bundle"

See Also
--------

- :doc:`plugin_framework` — runtime service plugins (``AicPlugin``, ``required_plugins``)
- :doc:`../user_guide/developing_apps` — control application development guide
- :doc:`../user_guide/architecture` — where capability discovery fits in the startup sequence
