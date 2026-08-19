from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import DOMAIN


@dataclass
class CatchSolarRuntimeData:
    """Per-config-entry objects that live only while the entry is loaded."""

    coordinator: Any
    runtime_tracker: Any
    daily_energy_coordinator: Any = None
    live_coordinator: Any = None
    live_client: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "coordinator": self.coordinator,
            "runtime_tracker": self.runtime_tracker,
            "daily_energy_coordinator": self.daily_energy_coordinator,
            "live_coordinator": self.live_coordinator,
            "live_client": self.live_client,
        }


def get_runtime_data(hass, entry) -> dict[str, Any]:
    """Return typed runtime data, with a test/backward-compatibility fallback."""
    runtime_data = getattr(entry, "runtime_data", None)
    if isinstance(runtime_data, CatchSolarRuntimeData):
        return runtime_data.as_dict()
    return hass.data[DOMAIN][entry.entry_id]
