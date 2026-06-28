from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import CatchSolarCoordinatorEntity, CatchSolarLocationEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [CatchSolarPrimaryLoadStateBinarySensor(coordinator)]
    for device in coordinator.data.get("devices", []):
        device_id = device.get("id")
        if device_id is None:
            continue
        entities.append(CatchSolarLoadStateBinarySensor(coordinator, device_id))
        entities.append(CatchSolarOnlineBinarySensor(coordinator, device_id))
    async_add_entities(entities)


class CatchSolarLoadStateBinarySensor(CatchSolarCoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_load_state"
        self._attr_name = "Load State"

    @property
    def is_on(self) -> bool:
        device = self.catchsolar_device or {}
        return int(device.get("load_state", 0)) == 1

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        device = self.catchsolar_device or {}
        return {
            "raw_load_state": device.get("load_state"),
            "is_primary_device": self._device_id == self.coordinator.data.get("primary_device_id"),
        }


class CatchSolarPrimaryLoadStateBinarySensor(CatchSolarLocationEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        location_id = coordinator.data.get("location", {}).get("id", "unknown")
        self._attr_unique_id = f"{location_id}_primary_load_state"
        self._attr_name = f"{self.primary_load_label} State"

    @property
    def is_on(self) -> bool:
        primary = self.coordinator.data.get("primary_device_id")
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == primary:
                return int(device.get("load_state", 0)) == 1
        return False

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        primary = self.coordinator.data.get("primary_device_id")
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == primary:
                return {
                    "raw_load_state": device.get("load_state"),
                    "primary_device_id": primary,
                    "primary_device_name": device.get("device_name"),
                }
        return {"primary_device_id": primary}


class CatchSolarOnlineBinarySensor(CatchSolarCoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_online"
        self._attr_name = "Online"

    @property
    def is_on(self) -> bool:
        device = self.catchsolar_device or {}
        return int(device.get("online", 0)) == 1

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        device = self.catchsolar_device or {}
        return {
            "impl_class": device.get("impl_class"),
            "is_primary_device": self._device_id == self.coordinator.data.get("primary_device_id"),
        }
