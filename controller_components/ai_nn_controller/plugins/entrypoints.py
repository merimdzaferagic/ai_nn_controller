# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Entry-point discovery for framework/application plugin bootstrapping."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from importlib.metadata import entry_points
from inspect import signature

from ..config import vprint
from ..managers.AicManager import AicManager
from ..registry import list_commands
from .metadata import CapabilityMetadata
from .registry import PluginRegistry

ENTRYPOINT_GROUP = "ai_nn_controller.app_init"
_loaded = False


def _parse_entrypoint_name(spec: str) -> tuple[str, str, str]:
    """Parse entry-point name into (bundle_name, app_module, commands_module)."""
    parts = [p.strip() for p in spec.split(":") if p.strip()]
    bundle_name = parts[0] if parts else spec

    app_module = "aic_app"
    commands_module = "commands"

    if len(parts) >= 2:
        app_module = parts[1]
    if len(parts) >= 3:
        commands_module = parts[2]

    return bundle_name, app_module, commands_module


def bootstrap_application_bundle(ep=None) -> None:
    """Generic app-bundle bootstrap callable used by app entry points."""
    spec = getattr(ep, "name", "") or "app_bundle"
    bundle_name, app_module_name, commands_module_name = _parse_entrypoint_name(spec)

    existing_apps = set(AicManager.aic_apps.keys())
    existing_commands = set(list_commands())

    command_capabilities: list[str] = []

    try:
        commands_module = import_module(commands_module_name)

        register_fn = getattr(commands_module, "register_specific_commands", None)
        if callable(register_fn):
            register_fn()

        get_caps_fn = getattr(commands_module, "get_command_capabilities", None)
        if callable(get_caps_fn):
            command_capabilities = list(get_caps_fn())
    except Exception as exc:
        vprint(f"[PluginEntrypoints] Command bootstrap warning for {bundle_name}: {exc}")

    import_module(app_module_name)

    new_apps = sorted(set(AicManager.aic_apps.keys()) - existing_apps)

    if not command_capabilities:
        command_capabilities = sorted(set(list_commands()) - existing_commands)

    PluginRegistry.register(
        CapabilityMetadata(
            name=bundle_name,
            plugin_type="app_bundle",
            capabilities=command_capabilities,
            extra={
                "entrypoint": app_module_name,
                "registered_apps": new_apps,
            },
        )
    )


def load_app_entrypoints(group: str = ENTRYPOINT_GROUP) -> None:
    """Load and execute registered app initialization hooks once per process."""
    global _loaded
    if _loaded:
        return

    try:
        selected = entry_points().select(group=group)
    except Exception as exc:
        vprint(f"[PluginEntrypoints] Failed to read entry points for group '{group}': {exc}")
        _loaded = True
        return

    for ep in selected:
        try:
            hook = ep.load()
            if isinstance(hook, Callable):
                try:
                    params = signature(hook).parameters
                    if len(params) == 0:
                        hook()
                    else:
                        hook(ep)
                except (TypeError, ValueError):
                    hook()
                vprint(f"[PluginEntrypoints] Loaded: {ep.name} ({ep.value})")
            else:
                vprint(f"[PluginEntrypoints] Skipped non-callable hook: {ep.name} ({ep.value})")
        except Exception as exc:
            vprint(f"[PluginEntrypoints] Failed to load {ep.name} ({ep.value}): {exc}")

    _loaded = True
