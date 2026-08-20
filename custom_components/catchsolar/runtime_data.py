from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import CatchSolarDataUpdateCoordinator
    from .runtime import PrimaryLoadRuntimeTracker
    from .telemetry import (
        CatchSolarDailyEnergyCoordinator,
        CatchSolarLiveClient,
        CatchSolarLiveCoordinator,
    )


@dataclass
class CatchSolarRuntimeData:
    """Per-config-entry objects that live only while the entry is loaded."""

    coordinator: CatchSolarDataUpdateCoordinator
    runtime_tracker: PrimaryLoadRuntimeTracker
    daily_energy_coordinator: CatchSolarDailyEnergyCoordinator | None = None
    live_coordinator: CatchSolarLiveCoordinator | None = None
    live_client: CatchSolarLiveClient | None = None


type CatchSolarConfigEntry = ConfigEntry[CatchSolarRuntimeData]


def get_runtime_data(entry: CatchSolarConfigEntry) -> CatchSolarRuntimeData:
    """Return the objects owned by a loaded config entry."""
    return entry.runtime_data
