# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
AIC Application Manager.

This module provides the centralized manager for all AIC applications in the
ai_nn_controller framework. AicManager acts
as a singleton registry that tracks all registered applications, their FastAPI
routers, and provides access to the controller for state management operations.

The framework is domain-agnostic and supports any type of network node including
optical, wireless, RAN, core network, and more.

The manager serves as the bridge between:
- The @aic_app decorator (which registers apps)
- The AicController (which manages app lifecycle)
- The FastAPI server (which exposes REST endpoints)
- The MCP integration (which generates AI tools)
"""

from ..config import vprint


class AicManager:
    """
    Centralized manager for AIC applications.

    This class maintains a registry of all AIC applications and provides
    methods for application lifecycle management. It operates as a singleton
    through class-level attributes.

    Attributes:
        aic_apps (dict): Registry of all applications, keyed by app name.
            Values are the AicApp subclass definitions.
        routers (dict): FastAPI routers for each application, keyed by app name.
        controller_instance (AicController): Reference to the active controller
            for delegating state management operations.

    Note:
        This class uses class methods exclusively - it should not be instantiated.
        All methods operate on class-level state shared across the application.
    """

    aic_apps = {}
    routers = {}
    controller_instance = None

    @classmethod
    def add_aic_app(cls, name, aic_app):
        """
        Register an AIC application with the manager.

        Called by the @aic_app decorator to register applications with the
        framework. Each application must have a unique name.

        Args:
            name (str): Unique identifier for the application.
            aic_app (type): The AicApp subclass to register.

        Raises:
            RuntimeError: If an application with the same name already exists.

        Example:
            This method is typically called internally by the decorator::

                @aic_app(name="MyApp")
                class MyApp(AicApp):
                    pass
                # Internally calls: AicManager.add_aic_app("MyApp", MyApp)
        """
        vprint("Registering aic_app with name %s." % name)
        if name in cls.aic_apps:
            raise RuntimeError("An aic_app with that name already exists.")

        cls.aic_apps[name] = aic_app

    @classmethod
    def add_router(cls, name, router):
        """
        Register a FastAPI router for an application.

        Each AIC application gets its own router with endpoints for
        state management, measurements, and control commands.

        Args:
            name (str): Application name (must match registered app).
            router (APIRouter): FastAPI router with app-specific endpoints.
        """
        vprint(f"Registering FastAPI router for app '{name}'")
        cls.routers[name] = router

    @classmethod
    def get_routers(cls):
        """
        Get all registered FastAPI routers.

        Returns:
            dict: Dictionary of routers keyed by application name.
        """
        return cls.routers

    @classmethod
    def set_controller(cls, controller):
        """
        Set the AicController instance for state management.

        Called during controller initialization to establish the connection
        between the manager and the runtime controller.

        Args:
            controller (AicController): The active controller instance.
        """
        cls.controller_instance = controller

    @classmethod
    def update_state(cls, app_name: str, state: str):
        """
        Update the state of an AIC application.

        Delegates to AicController.update_app_state() to handle state
        transitions and thread management.

        Args:
            app_name (str): Name of the application to update.
            state (str): New state - one of "running", "paused", or "stopped".

        Returns:
            dict: Result containing app name, new state, and previous state.

        Raises:
            RuntimeError: If AicController has not been initialized.
            ValueError: If app_name doesn't exist or state is invalid.
        """
        if cls.controller_instance is None:
            raise RuntimeError("AicController not initialized")
        return cls.controller_instance.update_app_state(app_name, state)

    @classmethod
    def get_app_state(cls, app_name: str):
        """
        Get the current state of an AIC application.

        Args:
            app_name (str): Name of the application to query.

        Returns:
            str: Current state - "running", "paused", or "stopped".

        Raises:
            RuntimeError: If AicController has not been initialized.
            ValueError: If app_name doesn't exist.
        """
        if cls.controller_instance is None:
            raise RuntimeError("AicController not initialized")
        return cls.controller_instance.get_app_state(app_name)

    @classmethod
    def get_measurements(cls, app_name: str):
        """
        Get the latest measurements for an AIC application.

        Retrieves the most recent measurement data from all nodes
        monitored by the specified application.

        Args:
            app_name (str): Name of the application to query.

        Returns:
            dict: Dictionary keyed by node_id containing the latest
                measurement for each monitored node. Returns empty dict
                if app is not running.

        Raises:
            RuntimeError: If AicController has not been initialized.
            ValueError: If app_name doesn't exist.
        """
        if cls.controller_instance is None:
            raise RuntimeError("AicController not initialized")
        return cls.controller_instance.get_app_measurements(app_name)

    @classmethod
    def send_manual_control(cls, app_name: str, node_id: int, command: dict):
        """
        Send a manual control command via an application.

        Allows external systems (REST API, MCP tools) to send commands
        to network nodes through a specific application.

        Args:
            app_name (str): Name of the application to send through.
            node_id (int): Target node ID for the command.
            command (dict): Command specification containing:
                - command (str): Command name (e.g., "SET_GAIN")
                - payload (dict): Command-specific parameters

        Returns:
            dict: Result containing app name, node_id, command, and status.

        Raises:
            RuntimeError: If AicController has not been initialized.
            ValueError: If app_name doesn't exist or node_id is not
                monitored by the application.
        """
        if cls.controller_instance is None:
            raise RuntimeError("AicController not initialized")
        return cls.controller_instance.send_manual_control(app_name, node_id, command)
