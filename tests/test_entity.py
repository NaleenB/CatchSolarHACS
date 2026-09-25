from __future__ import annotations

from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.catchsolar import entity as entity_module
from custom_components.catchsolar.binary_sensor import (
    CatchSolarLoadStateBinarySensor,
    CatchSolarPrimaryLoadStateBinarySensor,
)
from custom_components.catchsolar.const import DOMAIN
from custom_components.catchsolar.entity import CatchSolarCoordinatorEntity
from custom_components.catchsolar.sensor import (
    CatchSolarPrimaryLoadRuntimeSensor,
    CatchSolarPrimaryLoadStateRawSensor,
)
from custom_components.catchsolar.telemetry_sensor import (
    CatchSolarActorSocSensor,
    CatchSolarActorStateSensor,
    CatchSolarChannelPowerSensor,
    CatchSolarDailyEnergySensor,
    CatchSolarLiveSiteSensor,
    setup_telemetry_sensors,
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
        "Primary Load Runtime Today",
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
    actor_state = CatchSolarActorStateSensor(coordinator, "actor-1")
    actor_soc = CatchSolarActorSocSensor(coordinator, "actor-1")
    channel = CatchSolarChannelPowerSensor(coordinator, "LOAD:Hot Water")

    assert mains.native_value == -250
    assert mains.extra_state_attributes["sign_convention"] == ("positive import, negative export")
    assert actor_state.native_value == "CHARGING"
    assert actor_soc.native_value == 73
    assert actor_state.device_info["name"] == "Battery"
    assert channel.native_value == 3600
    assert channel.extra_state_attributes["channel_type"] == "LOAD"


def _build_live_coordinator(**overrides) -> SimpleNamespace:
    data: dict = {
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
    }
    data.update(overrides)
    return SimpleNamespace(data=data, config={}, last_update_success=True)


def test_child_device_links_to_location_device_by_registry_id(monkeypatch) -> None:
    """DeviceInfo must use the parent's registry id when HA supports it."""
    monkeypatch.setattr(entity_module, "_DEVICE_INFO_KEYS", {"via_device_id": str})
    coordinator = _build_coordinator()
    coordinator.location_device_id = "parent-device-id"

    device_info = CatchSolarCoordinatorEntity(coordinator, 88888).device_info

    assert device_info["via_device_id"] == "parent-device-id"
    assert "via_device" not in device_info


def test_child_device_falls_back_to_via_device_identifier(monkeypatch) -> None:
    """Older Home Assistant builds only understand the identifier tuple."""
    monkeypatch.setattr(entity_module, "_DEVICE_INFO_KEYS", {"via_device": tuple})
    coordinator = _build_coordinator()
    coordinator.location_device_id = "parent-device-id"

    device_info = CatchSolarCoordinatorEntity(coordinator, 88888).device_info

    assert device_info["via_device"] == (DOMAIN, "location_99999")
    assert "via_device_id" not in device_info


def test_child_device_omits_parent_link_without_a_parent(monkeypatch) -> None:
    monkeypatch.setattr(entity_module, "_DEVICE_INFO_KEYS", {"via_device_id": str})
    coordinator = _build_coordinator()
    coordinator.data["location"] = {}

    device_info = CatchSolarCoordinatorEntity(coordinator, 88888).device_info

    assert "via_device_id" not in device_info
    assert "via_device" not in device_info


def test_live_actor_device_links_to_location_device(monkeypatch) -> None:
    monkeypatch.setattr(entity_module, "_DEVICE_INFO_KEYS", {"via_device_id": str})
    coordinator = _build_live_coordinator()
    coordinator.location_device_id = "parent-device-id"

    device_info = CatchSolarActorStateSensor(coordinator, "actor-1").device_info

    assert device_info["via_device_id"] == "parent-device-id"
    assert "via_device" not in device_info


def test_actor_and_channel_sensors_are_unavailable_without_a_reading() -> None:
    """A missing reading must read unavailable, never a plausible-looking value."""
    coordinator = _build_live_coordinator(
        actors=[
            {
                "id": "actor-1",
                "class": "BATT",
                "name": "Battery",
                "power": None,
                "state": None,
                "soc": None,
            }
        ],
        channels=[{"key": "LOAD:Hot Water", "name": "Hot Water", "type": "LOAD", "power": None}],
    )

    assert CatchSolarActorStateSensor(coordinator, "actor-1").available is False
    assert CatchSolarActorSocSensor(coordinator, "actor-1").available is False
    assert CatchSolarChannelPowerSensor(coordinator, "LOAD:Hot Water").available is False


def test_actor_and_channel_sensors_stay_available_with_a_reading() -> None:
    coordinator = _build_live_coordinator()

    assert CatchSolarActorStateSensor(coordinator, "actor-1").available is True
    assert CatchSolarActorSocSensor(coordinator, "actor-1").available is True
    assert CatchSolarChannelPowerSensor(coordinator, "LOAD:Hot Water").available is True


def test_live_discovery_skips_actor_power_but_keeps_state_and_soc() -> None:
    """Actor `pwr` is not a usable measurement, so no power entity is created.

    It reports 0 for a solar relay even while the load it controls is running,
    so the sensor read a permanent, plausible-looking 0 W.
    """
    live_coordinator = _build_live_coordinator()
    live_coordinator.async_add_listener = lambda _callback: lambda: None
    runtime_data = SimpleNamespace(
        daily_energy_coordinator=None,
        live_coordinator=live_coordinator,
    )
    entry = SimpleNamespace(async_on_unload=lambda _callback: None)
    added: list = []

    setup_telemetry_sensors(entry, runtime_data, added.extend)

    created = [type(entity).__name__ for entity in added]
    assert "CatchSolarActorStateSensor" in created
    assert "CatchSolarActorSocSensor" in created
    assert not any("ActorPower" in name for name in created)
