# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from controlled_entity import ControlledEntity, node, NodeRunner
import random
import time


@node(name="ROADM1")
class ROADM1Node(ControlledEntity):
    available_measurements = [
        "session_id",
        "roadm1_preamp_target_gain",
        "roadm1_preamp_gain_tilt",
        "roadm1_booster_target_gain",
        "roadm1_booster_gain_tilt",
    ]
    measurement_interval = 1.0

    def poll_measurements(self):
        return {
            "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
            "roadm1_preamp_target_gain": round(random.uniform(18.0, 22.0), 2),
            "roadm1_preamp_gain_tilt": round(random.uniform(-1.0, 1.0), 2),
            "roadm1_booster_target_gain": round(random.uniform(15.0, 20.0), 2),
            "roadm1_booster_gain_tilt": round(random.uniform(-1.5, 1.5), 2),
        }


if __name__ == "__main__":
    NodeRunner().run()
