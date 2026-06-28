from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACT_KEYS = {
    "accessToken",
    "password",
    "token",
    "username",
}


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: ("**REDACTED**" if key in REDACT_KEYS else redact_value(child))
            for key, child in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item) for item in value]

    return value
