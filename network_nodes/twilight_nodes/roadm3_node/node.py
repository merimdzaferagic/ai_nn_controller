# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Twilight Bridge Node for ROADM.

Polls the Twilight REST API for ROADM measurements (preamp, booster,
VOA attenuations, channel powers) and publishes them to the AIC
message broker.
"""

from controlled_entity import ControlledEntity, node, NodeRunner
import os
import time
from twilight_client import TwilightClient, compute_total_power, freq_to_channel, DEFAULT_SESSION_ID


@node(name="TwilightROADM")
class TwilightROADMNode(ControlledEntity):
    available_measurements = [
        "timestamp",
        "device_name",
        "device_type",
        "preamp_gain",
        "preamp_tilt",
        "booster_gain",
        "booster_tilt",
        "voa_demux",
        "voa_mux",
        "channel_powers_out",
    ]
    available_controls = ["SET_GAIN", "SET_TILT", "SET_VOA"]

    def setup(self):
        """Initialize Twilight REST client and cache schema paths."""
        self.twilight_url = os.getenv(
            "TWILIGHT_URL",
            self.config.get("twilight_url", "http://host.docker.internal:8000"),
        )
        self.device_name = os.getenv(
            "TWILIGHT_DEVICE_NAME",
            self.config.get("device_name", "ROADM1"),
        )
        self.measurement_interval = float(
            os.getenv("POLL_INTERVAL", self.config.get("poll_interval", 1.0))
        )
        self.session_id = os.getenv("TWILIGHT_SESSION_ID", DEFAULT_SESSION_ID)

        self.twilight = TwilightClient(base_url=self.twilight_url)
        self._paths = {}
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
            fields = schema.get("fields", [])

            for field in fields:
                path = field.get("path", "")
                path_lower = path.lower()

                if "pre" in path_lower and "target_gain" in path_lower:
                    self._paths["preamp_gain"] = path
                elif "pre" in path_lower and "gain_tilt" in path_lower:
                    self._paths["preamp_tilt"] = path

                if "booster" in path_lower and "target_gain" in path_lower:
                    self._paths["booster_gain"] = path
                elif "booster" in path_lower and "gain_tilt" in path_lower:
                    self._paths["booster_tilt"] = path

                if "demux" in path_lower and "channel_attenuations" in path_lower:
                    base = path.rsplit(".", 1)[0] if "." in path else path
                    self._paths["voa_demux_base"] = base
                elif "mux" in path_lower and "demux" not in path_lower and "channel_attenuations" in path_lower:
                    base = path.rsplit(".", 1)[0] if "." in path else path
                    self._paths["voa_mux_base"] = base

            print(f"Cached ROADM paths: {self._paths}")
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

            preamp_gain = None
            preamp_tilt = None
            if "preamp_gain" in self._paths:
                preamp_gain = self._get_nested_value(config, self._paths["preamp_gain"])
            if "preamp_tilt" in self._paths:
                preamp_tilt = self._get_nested_value(config, self._paths["preamp_tilt"])

            booster_gain = None
            booster_tilt = None
            if "booster_gain" in self._paths:
                booster_gain = self._get_nested_value(config, self._paths["booster_gain"])
            if "booster_tilt" in self._paths:
                booster_tilt = self._get_nested_value(config, self._paths["booster_tilt"])

            voa_demux = {}
            voa_mux = {}
            if "voa_demux_base" in self._paths:
                base = self._paths["voa_demux_base"]
                attens = self._get_nested_value(config, base)
                if isinstance(attens, dict):
                    voa_demux = {str(k): v for k, v in attens.items()}
            if "voa_mux_base" in self._paths:
                base = self._paths["voa_mux_base"]
                attens = self._get_nested_value(config, base)
                if isinstance(attens, dict):
                    voa_mux = {str(k): v for k, v in attens.items()}

            channel_powers_out = {}
            try:
                signals = self.twilight.measure_signals(
                    self.session_id, self.device_name, "out"
                )
                for sig in signals:
                    power = sig.get("power")
                    freq = sig.get("frequency")
                    if power is not None and power > -50 and freq:
                        ch = freq_to_channel(freq)
                        channel_powers_out[str(ch)] = round(power, 2)
            except Exception:
                pass

            return {
                "timestamp": time.time(),
                "device_name": self.device_name,
                "device_type": "roadm",
                "preamp_gain": preamp_gain if preamp_gain is not None else 18.0,
                "preamp_tilt": preamp_tilt if preamp_tilt is not None else 0.0,
                "booster_gain": booster_gain if booster_gain is not None else 16.0,
                "booster_tilt": booster_tilt if booster_tilt is not None else 0.0,
                "voa_demux": voa_demux,
                "voa_mux": voa_mux,
                "channel_powers_out": channel_powers_out,
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

            if "preamp_gain" in cmd and "preamp_gain" in self._paths:
                updates[self._paths["preamp_gain"]] = cmd["preamp_gain"]
            if "preamp_tilt" in cmd and "preamp_tilt" in self._paths:
                updates[self._paths["preamp_tilt"]] = cmd["preamp_tilt"]

            if "booster_gain" in cmd and "booster_gain" in self._paths:
                updates[self._paths["booster_gain"]] = cmd["booster_gain"]
            if "booster_tilt" in cmd and "booster_tilt" in self._paths:
                updates[self._paths["booster_tilt"]] = cmd["booster_tilt"]

            if "voa_demux" in cmd and "voa_demux_base" in self._paths:
                ch = cmd.get("channel")
                atten = cmd.get("attenuation", cmd.get("voa_demux"))
                if ch is not None and atten is not None:
                    path = f"{self._paths['voa_demux_base']}.{ch}"
                    updates[path] = atten
            if "voa_mux" in cmd and "voa_mux_base" in self._paths:
                ch = cmd.get("channel")
                atten = cmd.get("attenuation", cmd.get("voa_mux"))
                if ch is not None and atten is not None:
                    path = f"{self._paths['voa_mux_base']}.{ch}"
                    updates[path] = atten

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
