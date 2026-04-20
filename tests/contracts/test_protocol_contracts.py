# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from protocol.envelope import MessageEnvelope, decode_message, encode_message


def test_envelope_roundtrip():
    env = MessageEnvelope(message_type="measurement", source="node-1", payload={"x": 1})
    encoded = encode_message(env)
    decoded = decode_message(encoded)
    assert decoded["schema"] == "urn:ai-nnc:envelope:1"
    assert decoded["payload"]["x"] == 1
