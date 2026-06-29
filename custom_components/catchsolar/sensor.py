from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, RUNTIME_SENSOR_7D_ROLLING, RUNTIME_SENSOR_24H, RUNTIME_SENSOR_TOTAL
from .entity import CatchSolarCoordinatorEntity, CatchSolarLocationEntity

DEVICE_SENSOR_KEYS = {
    "load_state": "Load State Raw",
    "serial_number": "Serial Number",
    "device_type": "Device Type",
    "channel_1_type": "Channel 1 Type",
    "channel_2_type": "Channel 2 Type",
    "controlling_load": "Controlling Load",
    "controlling_inverter": "Controlling Inverter",
    "impl_class": "Implementation Class",
}

POWER_SENSOR_KEYS = {
    "solar_power": "Monocle Solar Power",
    "total_consumption_power": "Monocle Total Consumption Power",
    "export_import_power": "Monocle Export/Import Power",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [
        CatchSolarPrimaryLoadStateRawSensor(coordinator),
        CatchSolarPrimaryLoadRuntimeSensor(
            coordinator,
            RUNTIME_SENSOR_24H,
            "Primary Load Runtime 24h",
        ),
        CatchSolarPrimaryLoadRuntimeSensor(
            coordinator,
            RUNTIME_SENSOR_7D_ROLLING,
            "Primary Load Runtime 7d Rolling",
        ),
        CatchSolarPrimaryLoadRuntimeSensor(
            coordinator,
            RUNTIME_SENSOR_TOTAL,
            "Primary Load Runtime Total",
        ),
    ]

    for device in coordinator.data.get("devices", []):
        device_id = device.get("id")
        if device_id is None:
            continue
        for key, name in DEVICE_SENSOR_KEYS.items():
            entities.append(CatchSolarDeviceMetadataSensor(coordinator, device_id, key, name))

    power_data = (coordinator.data.get("power") or {}).get("series", {})
    if power_data is not None:
        for key, name in POWER_SENSOR_KEYS.items():
            entities.append(CatchSolarPowerSensor(coordinator, key, name))

    async_add_entities(entities)


class CatchSolarDeviceMetadataSensor(CatchSolarCoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device_id: int, key: str, name: str) -> None:
        super().__init__(coordinator, device_id)
        self._key = key
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_name = name

    @property
    def native_value(self):
        device = self.catchsolar_device or {}
        return device.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "is_primary_device": self._device_id == self.coordinator.data.get("primary_device_id"),
        }


class CatchSolarPrimaryLoadStateRawSensor(CatchSolarLocationEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._attr_unique_id = f"{location_id}_primary_load_state_raw"
        self._attr_name = f"{self.primary_load_label} State Raw"

    @property
    def native_value(self):
        primary = self.primary_device_entry or {}
        return primary.get("load_state")

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        primary = self.primary_device_entry or {}
        return {
            "primary_device_id": primary.get("id"),
            "primary_device_name": primary.get("device_name"),
        }


class CatchSolarPowerSensor(CatchSolarLocationEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._key = key
        self._attr_unique_id = f"{location_id}_{key}"
        self._attr_name = name

    @property
    def native_value(self):
        power = self.coordinator.data.get("power") or {}
        return (power.get("series") or {}).get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        power = self.coordinator.data.get("power") or {}
        timestamp_ms = power.get("timestamp_ms")
        timestamp_local = None
        if isinstance(timestamp_ms, (int, float)):
            timestamp_local = dt_util.as_local(
                dt_util.utc_from_timestamp(float(timestamp_ms) / 1000)
            ).isoformat()

        latest_non_null = (power.get("latest_non_null_series") or {}).get(self._key)

        return {
            "series_key": self._key,
            "series_resolution_seconds": 300,
            "timestamp_ms": timestamp_ms,
            "timestamp_local": timestamp_local,
            "latest_non_null_value": latest_non_null,
            "last_polled_at": self.coordinator.data.get("last_polled_at"),
        }


class CatchSolarPrimaryLoadRuntimeSensor(CatchSolarLocationEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, runtime_key: str, name: str) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._runtime_key = runtime_key
        self._attr_unique_id = f"{location_id}_{runtime_key}"
        self._attr_name = name

    @property
    def native_value(self):
        runtime = self.coordinator.data.get("runtime") or {}
        seconds_map = {
            RUNTIME_SENSOR_24H: runtime.get("runtime_24h_seconds"),
            RUNTIME_SENSOR_7D_ROLLING: runtime.get("runtime_7d_rolling_seconds"),
            RUNTIME_SENSOR_TOTAL: runtime.get("runtime_total_seconds"),
        }
        seconds = seconds_map.get(self._runtime_key)
        if not isinstance(seconds, (int, float)):
            return None
        return round(float(seconds) / 3600, 2)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        runtime = self.coordinator.data.get("runtime") or {}
        primary = self.primary_device_entry or {}
        seconds_map = {
            RUNTIME_SENSOR_24H: runtime.get("runtime_24h_seconds"),
            RUNTIME_SENSOR_7D_ROLLING: runtime.get("runtime_7d_rolling_seconds"),
            RUNTIME_SENSOR_TOTAL: runtime.get("runtime_total_seconds"),
        }
        return {
            "runtime_seconds": seconds_map.get(self._runtime_key),
            "primary_device_id": primary.get("id"),
            "primary_device_name": primary.get("device_name"),
            "primary_load_on": runtime.get("primary_load_on"),
            "current_interval_start": runtime.get("current_interval_start"),
            "last_processed_at": runtime.get("last_processed_at"),
        }
