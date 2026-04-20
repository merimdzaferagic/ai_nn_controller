# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from arbitration import CommandArbitrator
from safety import SafetyPolicyEngine


def test_safety_allows_all_commands_by_default():
    engine = SafetyPolicyEngine()
    ok, reason = engine.enforce("SET_GAIN")
    assert ok
    assert reason is None


def test_safety_blocks_blocklisted_command():
    engine = SafetyPolicyEngine()
    engine.register_blocklist(["DANGEROUS_CMD"])
    ok, reason = engine.enforce("DANGEROUS_CMD")
    assert not ok
    assert "blocked" in reason


def test_arbitrator_last_write_allows():
    arb = CommandArbitrator(strategy="last_write_wins")
    ok, _ = arb.allow(1, "SET_GAIN", {"value": 10})
    assert ok
