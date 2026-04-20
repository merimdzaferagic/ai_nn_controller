# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""Twilight Bridge Node for Terminal (End/Receiver).

Polls the Twilight REST API for terminal RX measurements including
OSNR, GSNR, and BER, and publishes them to the AIC message broker.
"""

from controlled_entity import ControlledEntity, node, NodeRunner
import os
import time
from twilight_client import TwilightClient, freq_to_channel, DEFAULT_SESSION_ID


@node(name="TwilightTerminalEnd")
class TwilightTerminalEndNode(ControlledEntity):
    available_measurements = [
        "timestamp",
        "device_name",
        "device_type",
        "rx_signals",
    ]
    measurement_interval = 1.0

    def setup(self):
        """Initialize Twilight REST client."""
        self.twilight_url = os.getenv(
            "TWILIGHT_URL",
            self.config.get("twilight_url", "http://host.docker.internal:8000"),
        )
        self.device_name = os.getenv(
            "TWILIGHT_DEVICE_NAME",
            self.config.get("device_name", "Terminal_End"),
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
            rx_signals = {}

            for ch in range(1, 7):
                port_name = f"rx_Ch{ch}"
                try:
                    signals = self.twilight.measure_signals(
                        self.session_id, self.device_name, port_name
                    )

                    if not signals:
                        continue

                    collision = len(signals) > 1
                    sig = signals[0]
                    freq = sig.get("frequency")
                    power = sig.get("power")

                    rx_signals[str(ch)] = {
                        "power": round(power, 2) if power is not None else -99.9,
                        "osnr": sig.get("osnr") if not collision else 0.0,
                        "gsnr": sig.get("gsnr") if not collision else 0.0,
                        "ber": sig.get("ber") if not collision else 1.0,
                        "frequency": freq,
                        "collision": collision,
                        "num_signals": len(signals),
                    }

                    if collision:
                        print(f"[COLLISION] rx_Ch{ch}: {len(signals)} signals detected!")
                except Exception:
                    pass

            return {
                "timestamp": time.time(),
                "device_name": self.device_name,
                "device_type": "terminal",
                "rx_signals": rx_signals,
            }
        except Exception as e:
            print(f"Error polling measurements: {e}")
            return None

    def handle_command(self, cmd):
        """Terminal end (receiver) nodes don't accept configuration commands."""
        print(f"[COMMAND] Received (read-only node): {cmd}")
        return False


if __name__ == "__main__":
    NodeRunner().run()
