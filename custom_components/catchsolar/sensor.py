from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RUNTIME_SENSOR_7D_ROLLING, RUNTIME_SENSOR_24H, RUNTIME_SENSOR_TOTAL
from .entity import CatchSolarCoordinatorEntity, CatchSolarLocationEntity
from .telemetry_sensor import setup_telemetry_sensors

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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    integration_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = integration_data["coordinator"]
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

    async_add_entities(entities)
    setup_telemetry_sensors(entry, integration_data, async_add_entities)


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
