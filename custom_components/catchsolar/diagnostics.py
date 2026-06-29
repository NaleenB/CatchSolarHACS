from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .diagnostics_helpers import redact_value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    return {
        "entry": redact_value(dict(entry.data)),
        "options": dict(entry.options),
        "data": redact_value(dict(coordinator.data)),
    }
