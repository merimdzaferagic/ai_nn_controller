# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
ConsolePlugin — a dummy plugin that prints to stdout.

This is the reference implementation showing the minimum required structure
for an ai_nn_controller plugin. Real plugins would replace the print calls
with SDK calls to InfluxDB, MLflow, Prometheus, etc.

Install:
    pip install -e plugins/console_plugin/

Usage in a control app:
    @aic_app(name="MyApp")
    class MyApp(AicApp):
        required_plugins = ["ConsolePlugin"]

        @classmethod
        def process(cls, measurements):
            console = cls.plugins["ConsolePlugin"]
            console.log("tick")
            console.log_measurement(8, measurements.get(8, [{}])[-1])
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

    # ------------------------------------------------------------------ #
    # Public API — callable from control apps via cls.plugins["ConsolePlugin"]
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    @classmethod
    def _print(cls, level: str, message: str) -> None:
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        print(f"{ts} {cls._prefix} [{level}] {message}")
