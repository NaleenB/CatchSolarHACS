from __future__ import annotations

from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.catchsolar.binary_sensor import (
    CatchSolarLoadStateBinarySensor,
    CatchSolarPrimaryLoadStateBinarySensor,
)
from custom_components.catchsolar.entity import CatchSolarCoordinatorEntity
from custom_components.catchsolar.sensor import (
    CatchSolarPrimaryLoadRuntimeSensor,
    CatchSolarPrimaryLoadStateRawSensor,
)
from custom_components.catchsolar.telemetry_sensor import (
    CatchSolarActorPowerSensor,
    CatchSolarActorSocSensor,
    CatchSolarActorStateSensor,
    CatchSolarChannelPowerSensor,
    CatchSolarDailyEnergySensor,
    CatchSolarLiveSiteSensor,
)


@pytest.fixture(autouse=True)
def _brisbane_timezone():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(ZoneInfo("Australia/Brisbane"))
    yield
    dt_util.set_default_time_zone(original)


def _build_coordinator() -> SimpleNamespace:
    return SimpleNamespace(
        data={
            "location": {"id": 99999, "name": "99999"},
            "primary_device_id": 88888,
            "last_polled_at": "2026-06-29T00:30:21+00:00",
            "runtime": {
                "runtime_24h_seconds": 8100,
                "runtime_7d_rolling_seconds": 37800,
                "runtime_total_seconds": 97200,
                "current_interval_start": None,
                "last_processed_at": "2026-06-29T00:30:21+00:00",
                "primary_load_on": False,
            },
            "devices": [
                {
                    "id": 88888,
                    "device_name": "Water Heater",
                    "device_type": "SR",
                    "serial_number": "ABC123",
                    "load_state": 1,
                    "online": 1,
                    "impl_class": "Relay",
                }
            ],
        },
        config={"primary_load_label": "Water Heater"},
    )


def test_coordinator_entity_exposes_catchsolar_device_without_shadowing_core_properties() -> None:
    entity = CatchSolarCoordinatorEntity(_build_coordinator(), 88888)

    assert entity.catchsolar_device == {
        "id": 88888,
        "device_name": "Water Heater",
        "device_type": "SR",
        "serial_number": "ABC123",
        "load_state": 1,
        "online": 1,
        "impl_class": "Relay",
    }
    assert "device_entry" not in CatchSolarCoordinatorEntity.__dict__


def test_load_state_binary_sensor_reads_primary_device_state() -> None:
    entity = CatchSolarLoadStateBinarySensor(_build_coordinator(), 88888)

    assert entity.is_on is True
    assert entity.extra_state_attributes["raw_load_state"] == 1


def test_binary_sensors_keep_missing_state_unknown() -> None:
    coordinator = _build_coordinator()
    coordinator.data["devices"][0]["load_state"] = None

    device_entity = CatchSolarLoadStateBinarySensor(coordinator, 88888)
    primary_entity = CatchSolarPrimaryLoadStateBinarySensor(coordinator)

    assert device_entity.is_on is None
    assert device_entity.available is True
    assert primary_entity.is_on is None


def test_primary_binary_sensor_is_unavailable_without_identified_primary_device() -> None:
    coordinator = _build_coordinator()
    coordinator.data["primary_device_id"] = None

    entity = CatchSolarPrimaryLoadStateBinarySensor(coordinator)

    assert entity.is_on is None
    assert entity.available is False


def test_device_info_uses_semantic_names_with_ids() -> None:
    entity = CatchSolarCoordinatorEntity(_build_coordinator(), 88888)

    assert entity.device_info["name"] == "Water Heater Relay 88888"


def test_location_runtime_sensor_uses_hours_and_rounding() -> None:
    entity = CatchSolarPrimaryLoadRuntimeSensor(
        _build_coordinator(),
        "runtime_total",
        "Primary Load Runtime Total",
    )

    assert entity.native_value == 27.0
    assert entity.extra_state_attributes["runtime_seconds"] == 97200


def test_location_device_name_avoids_bare_numeric_name() -> None:
    entity = CatchSolarPrimaryLoadRuntimeSensor(
        _build_coordinator(),
        "runtime_24h",
        "Primary Load Runtime 24h",
    )

    assert entity.device_info["name"] == "Catch Solar Location 99999"


def test_primary_location_entities_use_primary_load_label() -> None:
    coordinator = _build_coordinator()

    raw_sensor = CatchSolarPrimaryLoadStateRawSensor(coordinator)
    binary_sensor = CatchSolarPrimaryLoadStateBinarySensor(coordinator)

    assert raw_sensor.name == "Water Heater State Raw"
    assert binary_sensor.name == "Water Heater State"


def test_daily_energy_sensor_is_energy_dashboard_compatible() -> None:
    coordinator = SimpleNamespace(
        data={
            "location": {"id": 99999, "name": "Home"},
            "series": {"grid_import_energy": 4.321},
            "raw_total_wh": {"grid_import_energy": 4321},
            "window_start": "2026-08-12T14:00:00.000Z",
            "window_end": "2026-08-13T14:00:00.000Z",
            "last_polled_at": "2026-08-13T00:00:00+00:00",
        },
        config={},
        last_update_success=True,
    )

    entity = CatchSolarDailyEnergySensor(
        coordinator,
        "grid_import_energy",
        "Daily Grid Import",
    )

    assert entity.native_value == 4.321
    assert entity.extra_state_attributes["raw_total_wh"] == 4321
    assert entity.available is True


def test_live_entities_read_site_actor_and_channel_data() -> None:
    coordinator = SimpleNamespace(
        data={
            "location": {"id": 99999, "name": "Home"},
            "site_power": {"mains_power": -250},
            "limits": {},
            "actors": [
                {
                    "id": "actor-1",
                    "class": "BATT",
                    "name": "Battery",
                    "power": -1200,
                    "state": "CHARGING",
                    "soc": 73,
                }
            ],
            "channels": [
                {
                    "key": "LOAD:Hot Water",
                    "name": "Hot Water",
                    "type": "LOAD",
                    "power": 3600,
                }
            ],
            "last_event_at": "2026-08-13T00:00:00+00:00",
        },
        config={},
        last_update_success=True,
    )

    mains = CatchSolarLiveSiteSensor(
        coordinator,
        "mains_power",
        "Live Mains Power",
        "site_power",
    )
    actor_power = CatchSolarActorPowerSensor(coordinator, "actor-1")
    actor_state = CatchSolarActorStateSensor(coordinator, "actor-1")
    actor_soc = CatchSolarActorSocSensor(coordinator, "actor-1")
    channel = CatchSolarChannelPowerSensor(coordinator, "LOAD:Hot Water")

    assert mains.native_value == -250
    assert mains.extra_state_attributes["sign_convention"] == ("positive import, negative export")
    assert actor_power.native_value == -1200
    assert actor_state.native_value == "CHARGING"
    assert actor_soc.native_value == 73
    assert actor_power.device_info["name"] == "Battery"
    assert channel.native_value == 3600
    assert channel.extra_state_attributes["channel_type"] == "LOAD"
