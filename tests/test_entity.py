from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.binary_sensor import CatchSolarLoadStateBinarySensor
from custom_components.catchsolar.entity import CatchSolarCoordinatorEntity


def _build_coordinator() -> SimpleNamespace:
    return SimpleNamespace(
        data={
            "location": {"id": 8382, "name": "Catch Solar 8382"},
            "primary_device_id": 3649,
            "devices": [
                {
                    "id": 3649,
                    "device_name": "Water Heater",
                    "device_type": "SR",
                    "serial_number": "ABC123",
                    "load_state": 1,
                    "online": 1,
                    "impl_class": "Relay",
                }
            ],
        },
        config={},
    )


def test_coordinator_entity_exposes_catchsolar_device_without_shadowing_core_properties() -> None:
    entity = CatchSolarCoordinatorEntity(_build_coordinator(), 3649)

    assert entity.catchsolar_device == {
        "id": 3649,
        "device_name": "Water Heater",
        "device_type": "SR",
        "serial_number": "ABC123",
        "load_state": 1,
        "online": 1,
        "impl_class": "Relay",
    }
    assert not hasattr(type(entity), "device_entry")


def test_load_state_binary_sensor_reads_primary_device_state() -> None:
    entity = CatchSolarLoadStateBinarySensor(_build_coordinator(), 3649)

    assert entity.is_on is True
    assert entity.extra_state_attributes["raw_load_state"] == 1
