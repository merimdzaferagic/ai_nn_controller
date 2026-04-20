# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Shared Twilight REST API client for bridge nodes.

This module provides a lightweight REST client for communicating with the
Twilight optical network simulator, plus utility functions for signal
processing and schema path discovery.
"""

import requests
import math
from typing import Optional, Dict, List, Any


# =============================================================================
# SESSION CONFIGURATION
# =============================================================================
DEFAULT_SESSION_ID = "default_session"

# =============================================================================
# FREQUENCY CONSTANTS (C-band, ITU-T 50 GHz grid)
# =============================================================================
C_BAND_MIN_FREQ = 191350.0  # GHz - Start of C-band channel grid
CHANNEL_SPACING = 50.0       # GHz - ITU-T 50 GHz channel spacing


def freq_to_channel(frequency_ghz: float) -> int:
    """Convert frequency (GHz) to channel number."""
    return int(round((frequency_ghz - C_BAND_MIN_FREQ) / CHANNEL_SPACING)) + 1


def channel_to_freq(channel: int) -> float:
    """Convert channel number to frequency (GHz)."""
    return C_BAND_MIN_FREQ + (channel - 1) * CHANNEL_SPACING


# =============================================================================
# TWILIGHT REST CLIENT
# =============================================================================
class TwilightClient:
    """Lightweight REST client for Twilight API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_v1 = f"{self.base_url}/api/v1"
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        """GET request helper."""
        url = f"{self.api_v1}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: Dict) -> Any:
        """PATCH request helper."""
        url = f"{self.api_v1}{path}"
        resp = self.session.patch(url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: Optional[Dict] = None) -> Any:
        """POST request helper."""
        url = f"{self.api_v1}{path}"
        resp = self.session.post(url, json=data or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_sessions(self) -> List[Dict]:
        """List all available sessions."""
        return self._get("/sessions/")

    def get_session(self, session_id: str) -> Dict:
        """Get session details."""
        return self._get(f"/sessions/{session_id}")

    def measure_signals(self, session_id: str, osub: str, port: str) -> List[Dict]:
        """Measure signals at a device port."""
        return self._get(f"/sessions/{session_id}/signals/measure/{osub}/{port}")

    def get_device_config(self, session_id: str, device_name: str) -> Dict:
        """Get device configuration via context endpoint."""
        context = self._get(f"/sessions/{session_id}/devices/{device_name}/context")
        return context.get("config", {})

    def get_device_config_schema(self, session_id: str, device_name: str, flat: bool = True) -> Dict:
        """Get device config schema (flat format for path discovery)."""
        params = {"flat": str(flat).lower()}
        return self._get(f"/sessions/{session_id}/devices/{device_name}/config/schema", params=params)

    def configure_device(self, session_id: str, device_name: str, updates: Dict) -> Dict:
        """Update device configuration."""
        return self._patch(f"/sessions/{session_id}/devices/{device_name}/config", updates)


# =============================================================================
# SIGNAL PROCESSING UTILITIES
# =============================================================================
def compute_total_power(signals: List[Dict], min_power: float = -50.0) -> float:
    """Compute total power from a list of signal measurements.

    Args:
        signals: List of signal dicts with 'power' field (dBm)
        min_power: Minimum power threshold to include signal

    Returns:
        Total power in dBm, or -100.0 if no valid signals
    """
    total_linear = 0.0
    for sig in signals:
        power = sig.get("power")
        if power is not None and power > min_power and not sig.get("is_ase_only", False):
            total_linear += 10 ** (power / 10.0)
    if total_linear > 0:
        return 10 * math.log10(total_linear)
    return -100.0


# =============================================================================
# SCHEMA PATH DISCOVERY UTILITIES
# =============================================================================
def find_schema_path(schema: Dict, contains: List[str], excludes: Optional[List[str]] = None) -> Optional[str]:
    """Find a config path in schema by matching keywords.

    Args:
        schema: Device config schema with 'fields' list
        contains: List of strings that must all appear in path (case-insensitive)
        excludes: List of strings that must NOT appear in path

    Returns:
        First matching path, or None if not found
    """
    excludes = excludes or []
    fields = schema.get("fields", [])
    for field in fields:
        path = field.get("path", "").lower()
        if all(c in path for c in contains):
            if not any(e in path for e in excludes):
                return field.get("path")
    return None


def get_amp_gain_path(schema: Dict, amp_type: str = "line") -> Optional[str]:
    """Get amplifier target_gain path based on amp type.

    Args:
        schema: Device config schema
        amp_type: One of "line", "preamp", "booster"

    Returns:
        Schema path for target_gain, or None if not found
    """
    if amp_type == "line":
        return find_schema_path(schema, ["target_gain"], ["pre_amp", "preamp", "booster", "bst"])
    elif amp_type == "preamp":
        return find_schema_path(schema, ["target_gain", "pre"], [])
    elif amp_type == "booster":
        return find_schema_path(schema, ["target_gain", "booster"], [])
    return None


def get_amp_tilt_path(schema: Dict, amp_type: str = "line") -> Optional[str]:
    """Get amplifier gain_tilt path based on amp type.

    Args:
        schema: Device config schema
        amp_type: One of "line", "preamp", "booster"

    Returns:
        Schema path for gain_tilt, or None if not found
    """
    if amp_type == "line":
        return find_schema_path(schema, ["gain_tilt"], ["pre_amp", "preamp", "booster", "bst"])
    elif amp_type == "preamp":
        return find_schema_path(schema, ["gain_tilt", "pre"], [])
    elif amp_type == "booster":
        return find_schema_path(schema, ["gain_tilt", "booster"], [])
    return None
