# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

import time
from typing import Optional, Tuple


class CommandArbitrator:
    def __init__(self, strategy: str = "last_write_wins"):
        self.strategy = strategy
        self.last_command_ts = {}

    def allow(self, node_id: int, command_name: str, payload: dict) -> Tuple[bool, Optional[str]]:
        key = (node_id, command_name)
        now = time.time()
        prev = self.last_command_ts.get(key, 0)
        if self.strategy == "min_gap" and now - prev < 0.2:
            return False, "Command conflict: duplicate command inside arbitration window"
        self.last_command_ts[key] = now
        return True, None
