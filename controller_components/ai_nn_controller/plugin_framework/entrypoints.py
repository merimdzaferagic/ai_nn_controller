# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Entry-point discovery for plugin package bootstrapping."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from importlib.metadata import entry_points
from inspect import signature

from ..config import vprint
from .plugin_manager import PluginManager

PLUGIN_ENTRYPOINT_GROUP = "ai_nn_controller.plugin_init"
_loaded = False


def _parse_plugin_entrypoint_name(spec: str) -> tuple[str, str]:
    """Parse entry-point name into (bundle_name, plugin_module)."""
    parts = [p.strip() for p in spec.split(":") if p.strip()]
    bundle_name = parts[0] if parts else spec
    plugin_module = parts[1] if len(parts) >= 2 else "aic_plugin"
    return bundle_name, plugin_module


def bootstrap_plugin_bundle(ep=None) -> None:
    """Generic plugin-bundle bootstrap callable used by plugin entry points."""
    spec = getattr(ep, "name", "") or "plugin_bundle"
    bundle_name, plugin_module_name = _parse_plugin_entrypoint_name(spec)

    existing_plugins = set(PluginManager.list_plugins())

    try:
        import_module(plugin_module_name)
    except Exception as exc:
        vprint(f"[PluginEntrypoints] Failed to import plugin module '{plugin_module_name}' "
               f"for bundle '{bundle_name}': {exc}")
        return

    new_plugins = sorted(set(PluginManager.list_plugins()) - existing_plugins)
    vprint(f"[PluginEntrypoints] Bundle '{bundle_name}' registered plugins: {new_plugins}")


def load_plugin_entrypoints(group: str = PLUGIN_ENTRYPOINT_GROUP) -> None:
    """Load and execute registered plugin initialisation hooks once per process."""
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
                vprint(f"[PluginEntrypoints] Skipped non-callable: {ep.name} ({ep.value})")
        except Exception as exc:
            vprint(f"[PluginEntrypoints] Failed to load {ep.name} ({ep.value}): {exc}")

    _loaded = True
