from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACT_KEYS = {
    "accessToken",
    "access_token",
    "accountId",
    "account_id",
    "address",
    "deviceId",
    "device_id",
    "email",
    "id",
    "locationId",
    "location_id",
    "password",
    "postcode",
    "serialNumber",
    "serial_number",
    "token",
    "username",
}
_REDACT_KEYS_CASEFOLD = {item.casefold() for item in REDACT_KEYS}


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: (
                "**REDACTED**"
                if isinstance(key, str) and key.casefold() in _REDACT_KEYS_CASEFOLD
                else redact_value(child)
            )
            for key, child in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item) for item in value]

    return value
