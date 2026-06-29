# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
AIC Plugin Base Classes.

Defines the interface every plugin must implement, plus optional typed mixin
base classes for common plugin categories (storage, model registry, monitoring).

Control applications declare which plugins they need via:

    class MyApp(AicApp):
        required_plugins = ["ConsolePlugin", "MLflow"]

        @classmethod
        def process(cls, measurements):
            cls.plugins["ConsolePlugin"].log("tick")

Plugins are deployed as independent Python packages and discovered at controller
startup via the ai_nn_controller.plugin_init entry-point group.
"""


class AicPlugin:
    """Base class for all AIC plugins."""

    plugin_type: str = "generic"
    u_name: str = ""

    @classmethod
    def connect(cls) -> None:
        """Initialise connection to the external service. Called at controller startup."""
        pass

    @classmethod
    def disconnect(cls) -> None:
        """Release resources. Called at controller shutdown."""
        pass

    @classmethod
    def is_healthy(cls) -> bool:
        """Return True if the plugin is operational."""
        return True


class StoragePlugin(AicPlugin):
    """Mixin for plugins that store and retrieve time-series or structured data (InfluxDB, ModelRDB, …)."""

    plugin_type = "storage"

    @classmethod
    def write(cls, key: str, value, tags: dict = None) -> None:
        raise NotImplementedError

    @classmethod
    def read(cls, query: str) -> list:
        raise NotImplementedError


class ModelRegistryPlugin(AicPlugin):
    """Mixin for plugins that manage ML model versioning (MLflow, …)."""

    plugin_type = "model_registry"

    @classmethod
    def load_model(cls, name: str, version: str = None):
        raise NotImplementedError

    @classmethod
    def save_model(cls, name: str, model, metrics: dict = None) -> None:
        raise NotImplementedError


class MonitoringPlugin(AicPlugin):
    """Mixin for plugins that push or pull observability metrics (Prometheus, …)."""

    plugin_type = "monitoring"

    @classmethod
    def push_metric(cls, name: str, value: float, labels: dict = None) -> None:
        raise NotImplementedError

    @classmethod
    def get_metric(cls, name: str, labels: dict = None) -> float:
        raise NotImplementedError
