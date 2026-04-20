# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="ROADM2")
class ROADM2Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "roadm2_preamp_target_gain",
        "roadm2_preamp_gain_tilt",
        "roadm2_booster_target_gain",
        "roadm2_booster_gain_tilt",
    ]
    measurement_interval = 1.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "roadm2_preamp_target_gain": round(random.uniform(17.0, 21.0), 2),
            "roadm2_preamp_gain_tilt": round(random.uniform(-1.5, 1.5), 2),
            "roadm2_booster_target_gain": round(random.uniform(14.0, 19.0), 2),
            "roadm2_booster_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
        }


if __name__ == "__main__":
    NodeRunner().run()
