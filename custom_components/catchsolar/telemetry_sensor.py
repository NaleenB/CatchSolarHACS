"""Live-telemetry and daily-energy sensors.

Keeping telemetry entities outside sensor.py keeps the core load-state and
runtime platform small and makes the two data paths easy to reason about.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LIVE_PUBLISH_INTERVAL_SECONDS
from .entity import CatchSolarLocationEntity

LIVE_SITE_POWER_SENSOR_KEYS = {
    "mains_power": "Live Mains Power",
    "solar_power": "Live Solar Power",
    "house_power": "Live House Power",
}

LIVE_LIMIT_SENSOR_KEYS = {
    "import_limit": "Live Import Limit",
    "active_control": "Live Active Control",
}

DAILY_ENERGY_SENSOR_KEYS = {
    "solar_yield_energy": "Daily Solar Yield",
    "grid_import_energy": "Daily Grid Import",
    "grid_export_energy": "Daily Grid Export",
    "house_consumption_energy": "Daily House Consumption",
    "consumed_solar_energy": "Daily Consumed Solar",
}


def setup_telemetry_sensors(
    entry: ConfigEntry,
    integration_data: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the optional live and daily-energy entities."""
    entities: list[SensorEntity] = []
    daily_energy_coordinator = integration_data.get("daily_energy_coordinator")
    if daily_energy_coordinator is not None:
        for key, name in DAILY_ENERGY_SENSOR_KEYS.items():
            entities.append(CatchSolarDailyEnergySensor(daily_energy_coordinator, key, name))

    live_coordinator = integration_data.get("live_coordinator")
    if live_coordinator is not None:
        for key, name in LIVE_SITE_POWER_SENSOR_KEYS.items():
            entities.append(CatchSolarLiveSiteSensor(live_coordinator, key, name, "site_power"))

    if entities:
        async_add_entities(entities)

    if live_coordinator is None:
        return

    # Keep discovered keys for the integration lifetime. Dynamic entities are
    # registered once, become unavailable when absent from a later payload,
    # and reuse the same entity when the upstream item reappears.
    seen: set[str] = set()

    def _discover_live_entities() -> None:
        new_entities: list[SensorEntity] = []
        actors = live_coordinator.data.get("actors", [])
        if any(actor.get("class") == "BATT" for actor in actors):
            seen_key = "site:battery_power"
            battery_power = (live_coordinator.data.get("site_power") or {}).get("battery_power")
            if battery_power is not None and seen_key not in seen:
                seen.add(seen_key)
                new_entities.append(
                    CatchSolarLiveSiteSensor(
                        live_coordinator,
                        "battery_power",
                        "Live Battery Power",
                        "site_power",
                    )
                )

        for key, name in LIVE_LIMIT_SENSOR_KEYS.items():
            seen_key = f"site:{key}"
            value = (live_coordinator.data.get("limits") or {}).get(key)
            if value is not None and seen_key not in seen:
                seen.add(seen_key)
                new_entities.append(CatchSolarLiveSiteSensor(live_coordinator, key, name, "limits"))

        for actor in actors:
            actor_id = actor["id"]
            candidates = (
                ("power", actor.get("power"), CatchSolarActorPowerSensor),
                ("state", actor.get("state"), CatchSolarActorStateSensor),
                ("soc", actor.get("soc"), CatchSolarActorSocSensor),
            )
            for suffix, value, entity_class in candidates:
                seen_key = f"actor:{actor_id}:{suffix}"
                if value is not None and seen_key not in seen:
                    seen.add(seen_key)
                    new_entities.append(entity_class(live_coordinator, actor_id))

        for channel in live_coordinator.data.get("channels", []):
            channel_key = channel["key"]
            seen_key = f"channel:{channel_key}:power"
            if channel.get("power") is not None and seen_key not in seen:
                seen.add(seen_key)
                new_entities.append(CatchSolarChannelPowerSensor(live_coordinator, channel_key))

        if new_entities:
            async_add_entities(new_entities)

    _discover_live_entities()
    remove_listener = live_coordinator.async_add_listener(_discover_live_entities)
    entry.async_on_unload(remove_listener)


class CatchSolarDailyEnergySensor(CatchSolarLocationEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._key = key
        self._attr_unique_id = f"{location_id}_{key}"
        self._attr_name = name

    @property
    def native_value(self):
        return (self.coordinator.data.get("series") or {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._key in (self.coordinator.data.get("series") or {})

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "raw_total_wh": (self.coordinator.data.get("raw_total_wh") or {}).get(self._key),
            "window_start": self.coordinator.data.get("window_start"),
            "window_end": self.coordinator.data.get("window_end"),
            "last_polled_at": self.coordinator.data.get("last_polled_at"),
        }


class CatchSolarLiveSiteSensor(CatchSolarLocationEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, key: str, name: str, section: str) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._key = key
        self._section = section
        self._attr_unique_id = f"{location_id}_live_{key}"
        self._attr_name = name

    @property
    def native_value(self):
        return (self.coordinator.data.get(self._section) or {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attributes: dict[str, object] = {
            "source": "Catch Power Socket.IO event",
            "last_event_at": self.coordinator.data.get("last_event_at"),
            "last_published_at": self.coordinator.data.get("last_published_at"),
            "publish_interval_seconds": LIVE_PUBLISH_INTERVAL_SECONDS,
        }
        if self._key == "mains_power":
            attributes["sign_convention"] = "positive import, negative export"
        elif self._key == "battery_power":
            attributes["sign_convention"] = "raw upstream value"
        return attributes


class CatchSolarLiveActorEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, actor_id: str) -> None:
        super().__init__(coordinator)
        self._actor_id = actor_id

    @property
    def actor(self) -> dict[str, Any] | None:
        for actor in self.coordinator.data.get("actors", []):
            if actor.get("id") == self._actor_id:
                return actor
        return None

    @property
    def available(self) -> bool:
        return super().available and self.actor is not None

    @property
    def device_info(self) -> DeviceInfo:
        actor = self.actor or {}
        location_id = self.coordinator.data.get("location", {}).get("id")
        return DeviceInfo(
            identifiers={(DOMAIN, f"location_{location_id}_actor_{self._actor_id}")},
            manufacturer="CATCH Power",
            model=actor.get("class") or "Controllable Device",
            name=actor.get("name") or f"Catch Solar Device {self._actor_id}",
            via_device=(DOMAIN, f"location_{location_id}"),
        )


class CatchSolarActorPowerSensor(CatchSolarLiveActorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_name = "Live Power"

    def __init__(self, coordinator, actor_id: str) -> None:
        super().__init__(coordinator, actor_id)
        location_id = self.coordinator.data.get("location", {}).get("id", "unknown")
        self._attr_unique_id = f"{location_id}_actor_{actor_id}_live_power"

    @property
    def native_value(self):
        return (self.actor or {}).get("power")


class CatchSolarActorStateSensor(CatchSolarLiveActorEntity, SensorEntity):
    _attr_name = "Live State"

    def __init__(self, coordinator, actor_id: str) -> None:
        super().__init__(coordinator, actor_id)
        location_id = self.coordinator.data.get("location", {}).get("id", "unknown")
        self._attr_unique_id = f"{location_id}_actor_{actor_id}_live_state"

    @property
    def native_value(self):
        return (self.actor or {}).get("state")


class CatchSolarActorSocSensor(CatchSolarLiveActorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Live State of Charge"

    def __init__(self, coordinator, actor_id: str) -> None:
        super().__init__(coordinator, actor_id)
        location_id = self.coordinator.data.get("location", {}).get("id", "unknown")
        self._attr_unique_id = f"{location_id}_actor_{actor_id}_live_soc"

    @property
    def native_value(self):
        return (self.actor or {}).get("soc")


class CatchSolarChannelPowerSensor(CatchSolarLocationEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, channel_key: str) -> None:
        super().__init__(coordinator)
        self._channel_key = channel_key
        channel = self.channel or {}
        location_id = self.location_entry.get("id", "unknown")
        self._attr_unique_id = f"{location_id}_channel_{channel_key}_live_power"
        self._attr_name = f"Live {channel.get('name') or 'Channel'} Power"

    @property
    def channel(self) -> dict[str, Any] | None:
        for channel in self.coordinator.data.get("channels", []):
            if channel.get("key") == self._channel_key:
                return channel
        return None

    @property
    def native_value(self):
        return (self.channel or {}).get("power")

    @property
    def available(self) -> bool:
        return super().available and self.channel is not None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        channel = self.channel or {}
        return {
            "channel_type": channel.get("type"),
            "source": "Catch Power Socket.IO event",
            "last_event_at": self.coordinator.data.get("last_event_at"),
            "last_published_at": self.coordinator.data.get("last_published_at"),
            "publish_interval_seconds": LIVE_PUBLISH_INTERVAL_SECONDS,
        }
