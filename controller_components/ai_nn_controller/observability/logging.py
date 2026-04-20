# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

import json
import time


def structured_log(event: str, level: str = "INFO", **fields):
    rec = {"ts": time.time(), "level": level, "event": event, **fields}
    print(json.dumps(rec, sort_keys=True))
