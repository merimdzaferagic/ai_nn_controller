# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Twilight Bridge Node for Amplifier.

Polls the Twilight REST API for amplifier measurements and publishes
them to the AIC message broker. Receives commands and applies them
via the Twilight API.
"""

from controlled_entity import ControlledEntity, node, NodeRunner
import os
import time
from twilight_client import (
    TwilightClient,
    compute_total_power,
    get_amp_gain_path,
    get_amp_tilt_path,
    DEFAULT_SESSION_ID,
)


@node(name="TwilightAmp")
class TwilightAmpNode(ControlledEntity):
    available_measurements = [
        "timestamp",
        "device_name",
        "device_type",
        "target_gain",
        "gain_tilt",
        "output_power",
        "input_power",
    ]
    available_controls = ["SET_GAIN", "SET_TILT"]

    def setup(self):
        """Initialize Twilight REST client and cache schema paths."""
        self.twilight_url = os.getenv(
            "TWILIGHT_URL",
            self.config.get("twilight_url", "http://host.docker.internal:8000"),
        )
        self.device_name = os.getenv(
            "TWILIGHT_DEVICE_NAME",
            self.config.get("device_name", "Amp_ila1"),
        )
        self.measurement_interval = float(
            os.getenv("POLL_INTERVAL", self.config.get("poll_interval", 1.0))
        )
        self.session_id = os.getenv("TWILIGHT_SESSION_ID", DEFAULT_SESSION_ID)

        self.twilight = TwilightClient(base_url=self.twilight_url)
        self._gain_path = None
        self._tilt_path = None
        self._detect_session()
        self._cache_schema_paths()

        print(f"Device: {self.device_name} at {self.twilight_url}")

    def _detect_session(self):
        if not self.session_id:
            try:
                sessions = self.twilight.list_sessions()
                if sessions:
                    self.session_id = sessions[0]["id"]
                    print(f"Auto-detected session: {self.session_id}")
                else:
                    print("WARNING: No sessions found. Will retry on first poll.")
            except Exception as e:
                print(f"WARNING: Could not list sessions: {e}. Will retry on first poll.")

    def _cache_schema_paths(self):
        if not self.session_id:
            return
        try:
            schema = self.twilight.get_device_config_schema(
                self.session_id, self.device_name, flat=True
            )
            self._gain_path = get_amp_gain_path(schema, "line")
            self._tilt_path = get_amp_tilt_path(schema, "line")
            print(f"Cached paths - gain: {self._gain_path}, tilt: {self._tilt_path}")
        except Exception as e:
            print(f"WARNING: Could not cache schema paths: {e}")

    def _get_nested_value(self, data, path):
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value

    def poll_measurements(self):
        if not self.session_id:
            self._detect_session()
            if not self.session_id:
                return None
            self._cache_schema_paths()

        try:
            config = self.twilight.get_device_config(self.session_id, self.device_name)

            target_gain = None
            gain_tilt = None

            if self._gain_path:
                target_gain = self._get_nested_value(config, self._gain_path)
            if self._tilt_path:
                gain_tilt = self._get_nested_value(config, self._tilt_path)

            # Fallback: try common paths
            if target_gain is None:
                target_gain = self._get_nested_value(config, "components.amp.target_gain")
            if gain_tilt is None:
                gain_tilt = self._get_nested_value(config, "components.amp.gain_tilt")

            output_power = -100.0
            input_power = -100.0
            try:
                out_signals = self.twilight.measure_signals(
                    self.session_id, self.device_name, "out"
                )
                output_power = compute_total_power(out_signals)
            except Exception:
                pass

            try:
                in_signals = self.twilight.measure_signals(
                    self.session_id, self.device_name, "in"
                )
                input_power = compute_total_power(in_signals)
            except Exception:
                pass

            return {
                "timestamp": time.time(),
                "device_name": self.device_name,
                "device_type": "amplifier",
                "target_gain": target_gain if target_gain is not None else 20.0,
                "gain_tilt": gain_tilt if gain_tilt is not None else 0.0,
                "output_power": round(output_power, 2),
                "input_power": round(input_power, 2),
            }
        except Exception as e:
            print(f"Error polling measurements: {e}")
            return None

    def handle_command(self, cmd):
        print(f"[COMMAND] Received: {cmd}")

        if not self.session_id:
            print("WARNING: No session ID, cannot apply command")
            return False

        try:
            updates = {}

            if "target_gain" in cmd or "amplifier_gain" in cmd:
                gain_value = cmd.get("target_gain") or cmd.get("amplifier_gain")
                if self._gain_path:
                    updates[self._gain_path] = gain_value
                else:
                    updates["components.amp.target_gain"] = gain_value

            if "gain_tilt" in cmd:
                if self._tilt_path:
                    updates[self._tilt_path] = cmd["gain_tilt"]
                else:
                    updates["components.amp.gain_tilt"] = cmd["gain_tilt"]

            if updates:
                self.twilight.configure_device(self.session_id, self.device_name, updates)
                print(f"[COMMAND] Applied: {updates}")
                return True

            return False
        except Exception as e:
            print(f"[COMMAND] Error: {e}")
            return False


if __name__ == "__main__":
    NodeRunner().run()
