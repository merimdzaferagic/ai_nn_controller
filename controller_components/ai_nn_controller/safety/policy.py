# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from typing import List, Optional, Tuple


class SafetyPolicyEngine:
    def __init__(self):
        self.blocked_commands = set()

    def register_blocklist(self, names: List[str]):
        self.blocked_commands.update(names)

    def enforce(self, command_name: str) -> Tuple[bool, Optional[str]]:
        if command_name in self.blocked_commands:
            return False, f"Command {command_name} blocked by policy"
        return True, None
