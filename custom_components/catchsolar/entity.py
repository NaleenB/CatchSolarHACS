from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PRIMARY_LOAD_LABEL, DEFAULT_PRIMARY_LOAD_LABEL, DOMAIN


def _clean_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _location_device_name(location: dict[str, Any]) -> str:
    location_id = location.get("id", "unknown")
    location_name = _clean_name(location.get("name"))
    if location_name and location_name != str(location_id):
        return f"{location_name} (Catch Solar Location {location_id})"
    return f"Catch Solar Location {location_id}"


def _relay_device_name(
    *,
    device: dict[str, Any],
    primary_device_id: int | None,
    primary_load_label: str,
) -> str:
    device_id = device.get("id", "unknown")
    if device.get("id") == primary_device_id:
        return f"{primary_load_label} Relay {device_id}"

    device_name = _clean_name(device.get("device_name"))
    if device_name and device_name != str(device_id):
        return f"{device_name} Relay {device_id}"
    return f"Catch Solar Relay {device_id}"


class CatchSolarCoordinatorEntity(CoordinatorEntity):
    def __init__(self, coordinator, device_id: int | None) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def catchsolar_device(self) -> dict[str, Any] | None:
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == self._device_id:
                return device
        return None

    @property
    def location_entry(self) -> dict[str, Any]:
        return self.coordinator.data.get("location", {})

    @property
    def primary_load_label(self) -> str:
        configured_label = self.coordinator.config.get(CONF_PRIMARY_LOAD_LABEL)
        if isinstance(configured_label, str):
            configured_label = configured_label.strip()
        return configured_label or DEFAULT_PRIMARY_LOAD_LABEL

    @property
    def device_info(self) -> DeviceInfo | None:
        device = self.catchsolar_device
        if device is None:
            return None
        via_location_id = self.location_entry.get("id")
        return DeviceInfo(
            identifiers={(DOMAIN, f"device_{device.get('id')}")},
            manufacturer="CATCH Power",
            model=device.get("device_type") or "Solar Relay",
            name=_relay_device_name(
                device=device,
                primary_device_id=self.coordinator.data.get("primary_device_id"),
                primary_load_label=self.primary_load_label,
            ),
            serial_number=device.get("serial_number"),
            via_device=(DOMAIN, f"location_{via_location_id}") if via_location_id is not None else None,
        )


class CatchSolarLocationEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    @property
    def location_entry(self) -> dict[str, Any]:
        return self.coordinator.data.get("location", {})

    @property
    def primary_load_label(self) -> str:
        configured_label = self.coordinator.config.get(CONF_PRIMARY_LOAD_LABEL)
        if isinstance(configured_label, str):
            configured_label = configured_label.strip()
        return configured_label or DEFAULT_PRIMARY_LOAD_LABEL

    @property
    def primary_device_entry(self) -> dict[str, Any] | None:
        primary_device_id = self.coordinator.data.get("primary_device_id")
        for device in self.coordinator.data.get("devices", []):
            if device.get("id") == primary_device_id:
                return device
        return None

    @property
    def device_info(self) -> DeviceInfo:
        location = self.location_entry
        location_id = location.get("id", "unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, f"location_{location_id}")},
            manufacturer="CATCH Power",
            model="Monocle Location",
            name=_location_device_name(location),
        )
