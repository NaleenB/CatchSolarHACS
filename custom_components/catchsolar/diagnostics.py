from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import EXPERIMENTAL_FEATURES
from .diagnostics_helpers import redact_value
from .runtime_data import get_runtime_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    integration_data = get_runtime_data(hass, entry)
    coordinator = integration_data["coordinator"]
    daily_energy_coordinator = integration_data.get("daily_energy_coordinator")
    live_coordinator = integration_data.get("live_coordinator")
    merged_config = {**entry.data, **entry.options}
    experimental_features = {}
    for feature_id, metadata in EXPERIMENTAL_FEATURES.items():
        runtime = integration_data.get(metadata["runtime_key"])
        experimental_features[feature_id] = {
            "introduced_in": metadata["introduced_in"],
            "option": metadata["option"],
            "enabled": bool(merged_config.get(metadata["option"], metadata["default"])),
            "loaded": runtime is not None,
            "last_update_success": (
                getattr(runtime, "last_update_success", None) if runtime is not None else None
            ),
        }

    return {
        "entry": redact_value(dict(entry.data)),
        "options": redact_value(dict(entry.options)),
        "experimental_features": experimental_features,
        "data": redact_value(dict(coordinator.data)),
        "daily_energy": (
            redact_value(dict(daily_energy_coordinator.data))
            if daily_energy_coordinator is not None
            else None
        ),
        "live": (
            redact_value(dict(live_coordinator.data)) if live_coordinator is not None else None
        ),
    }
