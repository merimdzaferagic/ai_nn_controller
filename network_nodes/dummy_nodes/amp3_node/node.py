# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="Amp3")
class Amp3Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "amp3_target_gain",
        "amp3_gain_tilt",
        "amp3_target_power",
        "amp3_control_mode",
    ]
    measurement_interval = 1.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "amp3_target_gain": round(random.uniform(14.0, 23.0), 2),
            "amp3_gain_tilt": round(random.uniform(-3.0, 3.0), 2),
            "amp3_target_power": round(random.uniform(1.0, 6.0), 2),
            "amp3_control_mode": 3,
        }


if __name__ == "__main__":
    NodeRunner().run()
