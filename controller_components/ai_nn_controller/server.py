# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
FastAPI Server for ai_nn_controller.

This module provides the REST API and MCP integration for managing AIC applications.
It can be used in two ways:

1. Via AicController(with_api=True).run() - Recommended for most use cases
2. Directly importing 'app' for custom server configurations

The create_app() function is called by AicController when with_api=True.
"""

import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .managers.AicManager import AicManager
from .mcp.fastapi_integration import create_mcp_router
from .mcp.tool_registry import MCPToolRegistry
from .config import vprint

# Global controller reference (set by create_app)
_controller = None


def create_app(controller=None):
    """
    Create and configure the FastAPI application.

    Args:
        controller: Optional AicController instance. If provided, the controller
                   will be started in a background thread. If None, a new controller
                   will be created.

    Returns:
        Configured FastAPI application instance.
    """
    global _controller
    _controller = controller

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Start the controller on startup and shut it down on exit."""
        global _controller
        vprint("[FastAPI] Starting controller in background thread...")

        if _controller is not None:
            def run_controller():
                try:
                    _controller._run_controller_only()
                except Exception as e:
                    vprint(f"[Background Error] Controller error: {e}")
                    import traceback
                    traceback.print_exc()

            threading.Thread(target=run_controller, daemon=True).start()
        else:
            def initialize_controller():
                global _controller
                try:
                    from .AicController import AicController
                    _controller = AicController()
                    _controller._run_controller_only()
                except Exception as e:
                    vprint(f"[Background Error] Failed to initialize controller: {e}")
                    import traceback
                    traceback.print_exc()

            threading.Thread(target=initialize_controller, daemon=True).start()

        vprint("[FastAPI] Server is ready to accept connections!")
        yield

        if _controller:
            vprint("[FastAPI] Shutting down controller...")
            try:
                _controller.shutdown()
                vprint("[FastAPI] Controller shut down successfully.")
            except Exception as e:
                vprint(f"[Shutdown Error] {e}")

    # Create FastAPI app
    app = FastAPI(
        title="AIC Application Controller API",
        description="Northbound API for managing AI Controller applications",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register app-specific routers
    vprint("[FastAPI] Registering app routers...")
    for name, router in AicManager.get_routers().items():
        app.include_router(router, prefix=f"/apps/{name}")
        vprint(f"[FastAPI] Registered router for app: {name}")
    vprint(f"[FastAPI] All apps registered: {list(AicManager.aic_apps.keys())}")

    # Register MCP router for AI agent integration
    vprint("[FastAPI] Registering MCP router...")
    mcp_router = create_mcp_router()
    app.include_router(mcp_router)
    mcp_stats = MCPToolRegistry.get_stats()
    vprint(f"[FastAPI] MCP router registered with {mcp_stats['total_tools']} tools")

    # =============================================================================
    # API Endpoints
    # =============================================================================

    @app.get("/")
    def root():
        """Root endpoint with API information."""
        return {
            "name": "AIC Application Controller API",
            "version": "1.0.0",
            "description": "Northbound API for managing AI Controller applications",
            "endpoints": {
                "apps": "/apps - List all registered applications",
                "health": "/health - Health check endpoint",
                "mcp": "/mcp - MCP (Model Context Protocol) endpoints for AI agents",
                "mcp_tools": "/mcp/tools - List available MCP tools",
                "docs": "/docs - Swagger UI documentation",
                "redoc": "/redoc - ReDoc documentation"
            }
        }

    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "controller_initialized": _controller is not None,
            "registered_apps": list(AicManager.aic_apps.keys())
        }

    @app.get("/apps")
    def list_apps():
        """List all registered aic_app instances with their current states."""
        apps = []
        for name, aic_app_cls in AicManager.aic_apps.items():
            state = "unknown"
            if _controller:
                try:
                    state = _controller.get_app_state(name)
                except Exception:
                    state = "not_initialized"

            apps.append({
                "name": name,
                "state": state,
                "node_id": getattr(aic_app_cls, 'node_id', None),
                "cell_ids": getattr(aic_app_cls, 'cell_ids', []),
                "time_interval": getattr(aic_app_cls, 'time_interval', None)
            })

        return {"apps": apps, "total": len(apps)}

    return app


# For backward compatibility - create a default app instance
# This allows existing code that imports 'from aic_interface.server import app' to still work
# Note: This will be created when the module is first imported
def _create_default_app():
    """Create default app for backward compatibility with run_server.py"""
    # Import apps to register them with AicManager
    vprint("[FastAPI] Importing and registering apps...")
    try:
        import aic_app
        vprint("[FastAPI] Apps imported successfully.")
    except ImportError as e:
        vprint(f"[FastAPI] Warning: Could not import aic_app: {e}")

    return create_app(controller=None)


# Lazy initialization - only create default app when accessed
_default_app = None


def get_app():
    """Get the default FastAPI app instance (creates it if needed)."""
    global _default_app
    if _default_app is None:
        _default_app = _create_default_app()
    return _default_app


# For backward compatibility with 'from aic_interface.server import app'
# We use a property-like access pattern
class _AppProxy:
    """Proxy class that lazily creates the app on first access."""

    def __getattr__(self, name):
        return getattr(get_app(), name)

    def __call__(self, *args, **kwargs):
        return get_app()(*args, **kwargs)


# This will be used by run_server.py for backward compatibility
app = _AppProxy()
