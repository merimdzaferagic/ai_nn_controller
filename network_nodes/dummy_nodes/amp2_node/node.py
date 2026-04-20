# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="Amp2")
class Amp2Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "amp2_target_gain",
        "amp2_gain_tilt",
        "amp2_target_power",
        "amp2_control_mode",
    ]
    measurement_interval = 1.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "amp2_target_gain": round(random.uniform(16.0, 24.0), 2),
            "amp2_gain_tilt": round(random.uniform(-2.5, 2.5), 2),
            "amp2_target_power": round(random.uniform(0.5, 4.5), 2),
            "amp2_control_mode": 3,
        }


if __name__ == "__main__":
    NodeRunner().run()
