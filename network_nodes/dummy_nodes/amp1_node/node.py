# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="Amp1")
class Amp1Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "amp1_target_gain",
        "amp1_gain_tilt",
        "amp1_target_power",
        "amp1_control_mode",
    ]
    measurement_interval = 1.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "amp1_target_gain": round(random.uniform(15.0, 25.0), 2),
            "amp1_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
            "amp1_target_power": round(random.uniform(0.0, 5.0), 2),
            "amp1_control_mode": 3,
        }


if __name__ == "__main__":
    NodeRunner().run()
