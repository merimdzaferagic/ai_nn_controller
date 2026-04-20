# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Twilight Bridge Node for Terminal (Source).

Polls the Twilight REST API for terminal TX measurements and publishes
them to the AIC message broker. Source terminals emit signals and can
adjust TX power.
"""

from controlled_entity import ControlledEntity, node, NodeRunner
import os
import time
from twilight_client import TwilightClient, freq_to_channel, channel_to_freq, DEFAULT_SESSION_ID


@node(name="TwilightTerminalSource")
class TwilightTerminalSourceNode(ControlledEntity):
    available_measurements = [
        "timestamp",
        "device_name",
        "device_type",
        "tx_signals",
    ]
    available_controls = ["SET_TX_POWER"]

    def setup(self):
        """Initialize Twilight REST client."""
        self.twilight_url = os.getenv(
            "TWILIGHT_URL",
            self.config.get("twilight_url", "http://host.docker.internal:8000"),
        )
        self.device_name = os.getenv(
            "TWILIGHT_DEVICE_NAME",
            self.config.get("device_name", "Terminal_Source"),
        )
        self.measurement_interval = float(
            os.getenv("POLL_INTERVAL", self.config.get("poll_interval", 1.0))
        )
        self.session_id = os.getenv("TWILIGHT_SESSION_ID", DEFAULT_SESSION_ID)

        self.twilight = TwilightClient(base_url=self.twilight_url)
        self._detect_session()

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

    def poll_measurements(self):
        if not self.session_id:
            self._detect_session()
            if not self.session_id:
                return None

        try:
            config = self.twilight.get_device_config(self.session_id, self.device_name)

            tx_signals = {}
            tx_config = config.get("tx_signals", [])
            if isinstance(tx_config, list):
                for sig in tx_config:
                    freq = sig.get("frequency_ghz")
                    power = sig.get("power_dbm")
                    if freq and power is not None:
                        ch = freq_to_channel(freq)
                        tx_signals[str(ch)] = {
                            "power": round(power, 2),
                            "frequency": freq,
                        }

            return {
                "timestamp": time.time(),
                "device_name": self.device_name,
                "device_type": "terminal",
                "tx_signals": tx_signals,
            }
        except Exception as e:
            print(f"Error polling measurements: {e}")
            return None

    def handle_command(self, cmd):
        """Handle TX power adjustment command.

        Supports two formats:
        - {'tx_power': value, 'channel': ch}  (explicit)
        - {'tx_power_ch_N': value}             (compact)
        """
        print(f"[COMMAND] Received: {cmd}")

        if not self.session_id:
            print("WARNING: No session ID, cannot apply command")
            return False

        try:
            tx_power = None
            channel = None

            if "tx_power" in cmd and "channel" in cmd:
                tx_power = cmd["tx_power"]
                channel = int(cmd["channel"])
            else:
                for key, val in cmd.items():
                    if key.startswith("tx_power_ch_"):
                        channel = int(key.split("_")[-1])
                        tx_power = val
                        break

            if tx_power is None or channel is None:
                print(f"[COMMAND] Unknown command format: {cmd}")
                return False

            config = self.twilight.get_device_config(self.session_id, self.device_name)
            tx_signals = config.get("tx_signals", [])

            target_freq = channel_to_freq(channel)
            found = False

            for sig in tx_signals:
                if abs(sig.get("frequency_ghz", 0) - target_freq) < 1.0:
                    sig["power_dbm"] = tx_power
                    found = True
                    break

            if found:
                self.twilight.configure_device(
                    self.session_id, self.device_name,
                    {"tx_signals": tx_signals},
                )
                print(f"[COMMAND] Applied TX power {tx_power:.2f} dBm to channel {channel}")
                return True

            print(f"[COMMAND] Channel {channel} not found in tx_signals")
            return False
        except Exception as e:
            print(f"[COMMAND] Error: {e}")
            return False


if __name__ == "__main__":
    NodeRunner().run()
