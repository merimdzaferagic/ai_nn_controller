# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Controlled Entity Base Class.

This module provides the base class for all network nodes within the ai_nn_controller
framework. Node developers inherit from ControlledEntity and implement their
specific measurement polling and command handling logic.

The framework is domain-agnostic and supports any type of network node including
optical, wireless, RAN, core network, and more.

Example:
    .. code-block:: python

        from controlled_entity import ControlledEntity, node, NodeRunner

        @node(name="MyAmplifier")
        class MyAmplifier(ControlledEntity):
            available_measurements = ["gain", "power", "tilt"]
            measurement_interval = 1.0

            def poll_measurements(self):
                return {
                    "gain": read_from_hardware(),
                    "power": read_from_hardware(),
                    "tilt": read_from_hardware(),
                }

        NodeRunner().run()

Note:
    The @node decorator must be applied to register the class with the
    framework before NodeRunner can use it.
"""


class ControlledEntity:
    """
    Base class for network nodes in the ai_nn_controller framework.

    Subclasses define their available measurements, optional control functions,
    and implement the southbound interface methods.

    Required Attributes (defined in subclass):
        available_measurements (list[str]): List of PM names this node exposes.
        measurement_interval (float): Seconds between measurement publishes.
            Default is 1.0.

    Optional Attributes:
        available_controls (list[str]): Control function names (e.g., ["SET_GAIN"]).
            Default is [] (measurement-only node).

    Auto-set Attributes (by @node decorator / NodeRunner):
        u_name (str): Set by @node decorator.
        config (dict): Parsed from node.conf, injected by NodeRunner.

    Southbound Interface (implement in subclass):
        poll_measurements() -> dict | None: Return current measurements.
        handle_command(payload: dict) -> bool: Apply a command (optional).
        setup() -> None: One-time initialization after registration (optional).
    """

    available_measurements = []
    available_controls = []
    measurement_interval = 1.0

    def poll_measurements(self):
        """
        Poll the southbound interface for current measurements.

        Called periodically at ``measurement_interval`` seconds by NodeRunner.
        Return a dict of measurement name -> value, or None if no data is
        available this cycle.

        Returns:
            dict: Measurement data, e.g. {"gain": 20.5, "power": -10.2}
            None: If no measurements are available this cycle.
        """
        raise NotImplementedError("Subclass must implement poll_measurements()")

    def handle_command(self, payload):
        """
        Handle an incoming command from an aic_app via the message bus.

        Override this method if your node accepts control commands.
        Measurement-only nodes do not need to implement this.

        Args:
            payload (dict): The command payload, e.g.
                {"target_gain": 20.0} or {"preamp_gain": 15.0}

        Returns:
            bool: True if command was applied successfully, False otherwise.
        """
        return False

    def setup(self):
        """
        One-time initialization hook called after registration completes
        but before the measurement/command loops start.

        Override to initialize southbound connections (REST clients,
        database connections, hardware interfaces, etc.).

        At this point ``self.config`` is available with parsed node.conf values.
        """
        pass
