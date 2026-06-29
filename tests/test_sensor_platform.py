from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.const import DOMAIN
from custom_components.catchsolar.sensor import (
    CatchSolarDeviceMetadataSensor,
    CatchSolarPowerSensor,
    CatchSolarPrimaryLoadRuntimeSensor,
    CatchSolarPrimaryLoadStateRawSensor,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_sensor_setup_adds_runtime_sensors_once_at_location_scope() -> None:
    coordinator = SimpleNamespace(
        data={
            "location": {"id": 99999, "name": "Home"},
            "primary_device_id": 88888,
            "devices": [
                {
                    "id": 88888,
                    "device_name": "Water Heater",
                    "serial_number": "ABC123",
                    "device_type": "SR",
                    "load_state": 1,
                    "online": 1,
                },
                {
                    "id": 77777,
                    "device_name": "Pool Pump",
                    "serial_number": "XYZ999",
                    "device_type": "SR",
                    "load_state": 0,
                    "online": 1,
                },
            ],
            "power": {
                "series": {
                    "solar_power": 1,
                    "total_consumption_power": 2,
                    "export_import_power": 3,
                }
            },
            "runtime": {
                "runtime_24h_seconds": 1,
                "runtime_7d_rolling_seconds": 2,
                "runtime_total_seconds": 3,
                "current_interval_start": None,
                "last_processed_at": None,
                "primary_load_on": False,
            },
        },
        config={"primary_load_label": "Water Heater"},
    )
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": {"coordinator": coordinator}}})
    entry = SimpleNamespace(entry_id="entry-1")
    added = []

    await async_setup_entry(hass, entry, added.extend)

    assert sum(isinstance(entity, CatchSolarPrimaryLoadStateRawSensor) for entity in added) == 1
    assert sum(isinstance(entity, CatchSolarPrimaryLoadRuntimeSensor) for entity in added) == 3
    assert sum(isinstance(entity, CatchSolarDeviceMetadataSensor) for entity in added) == 16
    assert sum(isinstance(entity, CatchSolarPowerSensor) for entity in added) == 3
