from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import CatchSolarCoordinatorEntity, CatchSolarLocationEntity
from .runtime_data import get_runtime_data


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = get_runtime_data(entry).coordinator
    async_add_entities([CatchSolarPrimaryLoadStateBinarySensor(coordinator)])
    seen_device_ids: set[int] = set()

    def _add_device_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for device in coordinator.data.get("devices", []):
            device_id = device.get("id")
            if not isinstance(device_id, int) or device_id in seen_device_ids:
                continue
            seen_device_ids.add(device_id)
            entities.append(CatchSolarLoadStateBinarySensor(coordinator, device_id))
            entities.append(CatchSolarOnlineBinarySensor(coordinator, device_id))
        if entities:
            async_add_entities(entities)

    _add_device_entities()
    remove_listener = coordinator.async_add_listener(_add_device_entities)
    entry.async_on_unload(remove_listener)


class CatchSolarLoadStateBinarySensor(CatchSolarCoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_load_state"
        self._attr_name = "Load State"

    @property
    def is_on(self) -> bool | None:
        device = self.catchsolar_device
        if device is None or device.get("load_state") is None:
            return None
        return device["load_state"] == 1

    @property
    def available(self) -> bool:
        return super().available and self.catchsolar_device is not None

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
    def is_on(self) -> bool | None:
        primary = self.coordinator.data.get("primary_device_id")
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == primary:
                load_state = device.get("load_state")
                return None if load_state is None else load_state == 1
        return None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("primary_device_id") is not None

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
    def is_on(self) -> bool | None:
        device = self.catchsolar_device
        if device is None or device.get("online") is None:
            return None
        return device["online"] == 1

    @property
    def available(self) -> bool:
        return super().available and self.catchsolar_device is not None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        device = self.catchsolar_device or {}
        return {
            "impl_class": device.get("impl_class"),
            "is_primary_device": self._device_id == self.coordinator.data.get("primary_device_id"),
        }
