# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from collections import deque
from ..managers.AicManager import AicManager
from ..mcp.tool_generator import MCPToolGenerator
from ..config import vprint
from .command_validator import register_app_validators
from .agent_controlled import register_app_agent_operations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional


class StateUpdateRequest(BaseModel):
    """Request model for state updates."""
    state: str


class ControlCommandRequest(BaseModel):
    """Request model for manual control commands."""
    node_id: int
    command: str
    payload: dict


def aic_app(name):
    """
    Decorator that registers an AIC application with the framework.

    This decorator:
    1. Registers the app with AicManager
    2. Creates FastAPI REST endpoints for the app
    3. Auto-generates MCP tools based on the app's capabilities
    4. Auto-derives cell_ids from read_measurements and control_functions keys
    5. Auto-initializes send_commands as an empty list

    Args:
        name: Unique name for the application

    Usage:
        @aic_app(name="MyNetworkApp")
        class MyNetworkApp(AicApp):
            read_measurements = {3: ["gain", "power"]}
            control_functions = {3: ["SET_GAIN"]}

            @classmethod
            def process(cls, measurements):
                # Custom control logic
                pass

    Note:
        cell_ids and send_commands do not need to be defined in your app class.
        They are automatically derived/initialized by this decorator.
    """
    def wrapper(cls):

        cls.u_name = name

        # Auto-derive cell_ids from read_measurements and control_functions keys
        read_node_ids = set(getattr(cls, 'read_measurements', {}).keys())
        control_node_ids = set(getattr(cls, 'control_functions', {}).keys())
        cls.cell_ids = sorted(read_node_ids | control_node_ids)

        # Auto-initialize send_commands as deque if not defined
        cls.send_commands = deque()

        # Initialize agent-controlled request queue and handler map
        cls.agent_requests = deque()
        cls._agent_handlers = {}

        # Per-class plugins dict — populated by AicController at startup
        # after all plugins have been loaded and validated.
        cls.plugins = {}

        AicManager.add_aic_app(name, cls)

        # Create FastAPI router for this app
        router = APIRouter(tags=[name])

        @router.get("/info")
        def get_app_info():
            """Get information about this aic_app."""
            return {
                "app_name": name,
                "aic_app_id": cls.aic_app_id,
                "cell_ids": cls.cell_ids,
                "control_loop_update_time": cls.control_loop_update_time,
                "read_measurements": cls.read_measurements,
                "control_functions": cls.control_functions,
            }

        @router.put("/state")
        def update_state(request: StateUpdateRequest):
            """Update the state of this aic_app (running, paused, stopped)."""
            try:
                result = AicManager.update_state(name, request.state)
                return result
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/state")
        def get_state():
            """Get the current state of this aic_app."""
            try:
                state = AicManager.get_app_state(name)
                return {"app": name, "state": state}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/measurements")
        def get_measurements():
            """Get the latest measurements for this aic_app."""
            try:
                measurements = AicManager.get_measurements(name)
                return {"app": name, "measurements": measurements}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/control")
        def send_control(request: ControlCommandRequest):
            """Send a manual control command to a node."""
            try:
                result = AicManager.send_manual_control(
                    name, request.node_id, {"command": request.command, "payload": request.payload}
                )
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Register the router with AicManager
        AicManager.add_router(name, router)
        cls.router = router

        # Register command validators defined in the app class
        # This scans for @command_validator decorated methods
        register_app_validators(cls, name)

        # Register agent-controlled operations defined in the app class
        # This scans for @agent_controlled decorated methods
        register_app_agent_operations(cls, name)

        # Auto-generate MCP tools from the app's capabilities
        try:
            mcp_tools = MCPToolGenerator.generate_tools_for_app(name, cls, AicManager)
            cls.mcp_tools = mcp_tools
            vprint(f"[MCP] Generated {len(mcp_tools)} tools for app '{name}'")
        except Exception as e:
            vprint(f"[MCP] Warning: Failed to generate MCP tools for '{name}': {e}")
            cls.mcp_tools = []

        return cls

    return wrapper
