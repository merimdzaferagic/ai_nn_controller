# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict


class EnvelopeValidationError(ValueError):
    pass


@dataclass
class MessageEnvelope:
    schema: str = "urn:ai-nnc:envelope:1"
    version: str = "1.0"
    message_type: str = "unknown"
    source: str = ""
    target: str = ""
    correlation_id: str = ""
    lineage_id: str = ""
    idempotency_key: str = ""
    ts: float = 0.0
    payload: Dict[str, Any] = None

    def to_dict(self) -> dict:
        if self.payload is None:
            self.payload = {}
        if not self.ts:
            self.ts = time.time()
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())
        if not self.lineage_id:
            self.lineage_id = self.correlation_id
        if not self.idempotency_key:
            self.idempotency_key = self.correlation_id
        return self.__dict__.copy()


def validate_envelope(data: dict) -> None:
    required = ["schema", "version", "message_type", "payload"]
    missing = [k for k in required if k not in data]
    if missing:
        raise EnvelopeValidationError(f"Missing envelope fields: {missing}")
    if data["schema"] != "urn:ai-nnc:envelope:1":
        raise EnvelopeValidationError("Unsupported schema")


def encode_message(envelope: MessageEnvelope) -> str:
    data = envelope.to_dict()
    validate_envelope(data)
    return json.dumps(data)


def decode_message(raw: str) -> dict:
    parsed = json.loads(raw)
    if isinstance(parsed, dict) and parsed.get("schema") == "urn:ai-nnc:envelope:1":
        validate_envelope(parsed)
        return parsed
    return parsed
