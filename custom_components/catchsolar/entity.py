from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class CatchSolarCoordinatorEntity(CoordinatorEntity):
    def __init__(self, coordinator, device_id: int | None) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_entry(self) -> dict[str, Any] | None:
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == self._device_id:
                return device
        return None

    @property
    def location_entry(self) -> dict[str, Any]:
        return self.coordinator.data.get("location", {})

    @property
    def device_info(self) -> DeviceInfo | None:
        device = self.device_entry
        if device is None:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, f"device_{device.get('id')}")},
            manufacturer="CATCH Power",
            model=device.get("device_type") or "Solar Relay",
            name=device.get("device_name") or device.get("serial_number") or "Catch Solar Device",
            serial_number=device.get("serial_number"),
        )


class CatchSolarLocationEntity(CoordinatorEntity):
    @property
    def location_entry(self) -> dict[str, Any]:
        return self.coordinator.data.get("location", {})

    @property
    def device_info(self) -> DeviceInfo:
        location = self.location_entry
        location_id = location.get("id", "unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, f"location_{location_id}")},
            manufacturer="CATCH Power",
            model="Monocle Location",
            name=location.get("name") or f"Catch Solar {location_id}",
        )
