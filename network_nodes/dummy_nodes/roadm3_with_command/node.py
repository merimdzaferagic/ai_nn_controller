# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="ROADM3")
class ROADM3Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "roadm3_preamp_target_gain",
        "roadm3_preamp_gain_tilt",
        "roadm3_booster_target_gain",
        "roadm3_booster_gain_tilt",
    ]
    available_controls = ["SET_GAIN", "SET_VOA", "SET_TILT"]
    measurement_interval = 5.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "roadm3_preamp_target_gain": round(random.uniform(17.0, 21.0), 2),
            "roadm3_preamp_gain_tilt": round(random.uniform(-1.5, 1.5), 2),
            "roadm3_booster_target_gain": round(random.uniform(14.0, 19.0), 2),
            "roadm3_booster_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
        }

    def handle_command(self, payload):
        print(f"[ROADM3] Processing command: {payload}")

        if "target_gain" in payload:
            print(f"[ROADM3] Setting target gain to: {payload['target_gain']}")

        if "preamp_gain" in payload:
            print(f"[ROADM3] Setting preamp gain to: {payload['preamp_gain']}")

        if "booster_gain" in payload:
            print(f"[ROADM3] Setting booster gain to: {payload['booster_gain']}")

        if "voa_mux" in payload:
            channel = payload.get("channel", "unknown")
            print(f"[ROADM3] Setting VOA MUX for channel {channel} to: {payload['voa_mux']}")

        print(f"[ROADM3] Command processing complete")
        return True


if __name__ == "__main__":
    NodeRunner().run()
