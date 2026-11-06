from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .api import CatchSolarApiClient, CatchSolarApiError
from .const import (
    CONF_OVERRIDE_DURATION,
    DEFAULT_OVERRIDE_DURATION_MINUTES,
    MAX_OVERRIDE_DURATION_MINUTES,
    MIN_OVERRIDE_DURATION_MINUTES,
    OVERRIDE_MODE_AUTO,
    OVERRIDE_MODES,
)
from .entity import CatchSolarLocationEntity
from .parsing import resolve_relay_actor_id
from .runtime_data import CatchSolarConfigEntry, get_runtime_data

_EXPIRES_AT_ATTRIBUTE = "override_expires_at"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CatchSolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime_data = get_runtime_data(entry)
    async_add_entities(
        [CatchSolarPrimaryLoadControlSelect(runtime_data.coordinator, entry)]
    )


class CatchSolarPrimaryLoadControlSelect(
    CatchSolarLocationEntity, SelectEntity, RestoreEntity
):
    """Manual override for the primary controlled load.

    ``auto`` removes any override so the relay's own schedule takes over.
    ``on`` and ``off`` write a time-limited override through the same API the
    Monocle app uses.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-boiler"
    _attr_options = OVERRIDE_MODES

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        location_id = self.location_entry.get("id", "unknown")
        self._attr_unique_id = f"{location_id}_primary_load_control"
        self._attr_name = f"{self.primary_load_label} Control"
        self._api: CatchSolarApiClient = coordinator.api
        self._option = OVERRIDE_MODE_AUTO
        self._expires_at: datetime | None = None
        self._actor_id: str | None = None
        self._unsub_expiry: Callable[[], None] | None = None

    @property
    def available(self) -> bool:
        return super().available and self.primary_device_entry is not None

    @property
    def current_option(self) -> str:
        return self._option

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "actor_id": self._actor_id,
            "override_duration_minutes": self._override_duration_minutes,
            _EXPIRES_AT_ATTRIBUTE: (
                self._expires_at.isoformat() if self._expires_at is not None else None
            ),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._restore_last_state(await self.async_get_last_state())
        try:
            await self._async_sync_override_state()
        except CatchSolarApiError:
            # Restoring the last known state is still useful when the screen
            # definition cannot be read during startup.
            pass
        self._schedule_expiry()

    def _restore_last_state(self, last_state) -> None:
        if last_state is None or last_state.state not in OVERRIDE_MODES:
            return
        if last_state.state == OVERRIDE_MODE_AUTO:
            self._option = OVERRIDE_MODE_AUTO
            return

        expires_at = _parse_expiry(last_state.attributes.get(_EXPIRES_AT_ATTRIBUTE))
        if expires_at is None or expires_at <= dt_util.utcnow():
            # Never restore a stale manual override; the relay's own timer has
            # already handed control back to the schedule by now.
            self._option = OVERRIDE_MODE_AUTO
            self._expires_at = None
            return

        self._option = last_state.state
        self._expires_at = expires_at

    async def _async_sync_override_state(self) -> None:
        location_id = self.location_entry.get("id")
        if not isinstance(location_id, int):
            return
        actor_id = await self._async_resolve_actor_id()
        state = await self._api.async_get_override_state(location_id, actor_id)
        mode = state.get("mode")
        if not isinstance(mode, str) or mode not in OVERRIDE_MODES:
            return
        expires_at = state.get("expires_at")
        if not isinstance(expires_at, datetime):
            expires_at = None
        if mode != OVERRIDE_MODE_AUTO and (
            expires_at is None or expires_at <= dt_util.utcnow()
        ):
            mode = OVERRIDE_MODE_AUTO
            expires_at = None
        self._option = mode
        self._expires_at = expires_at if mode != OVERRIDE_MODE_AUTO else None

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_expiry()
        await super().async_will_remove_from_hass()

    async def async_select_option(self, option: str) -> None:
        option = str(option).strip().lower()
        if option not in OVERRIDE_MODES:
            raise HomeAssistantError(f"Unsupported Catch Solar control mode: {option}")

        location_id = self.location_entry.get("id")
        if not isinstance(location_id, int):
            raise HomeAssistantError("Catch Solar location is not available")

        try:
            actor_id = await self._async_resolve_actor_id()
            if option == OVERRIDE_MODE_AUTO:
                await self._api.async_remove_override(location_id, actor_id)
                expires_at = None
            else:
                minutes = self._override_duration_minutes
                await self._api.async_save_override(
                    location_id,
                    actor_id,
                    option,
                    minutes,
                )
                expires_at = dt_util.utcnow() + timedelta(minutes=minutes)
        except CatchSolarApiError as err:
            raise HomeAssistantError(f"Catch Solar control failed: {err}") from err

        self._option = option
        self._expires_at = expires_at
        self._schedule_expiry()
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @property
    def _override_duration_minutes(self) -> int:
        config = getattr(self.coordinator, "config", {})
        configured = config.get(
            CONF_OVERRIDE_DURATION,
            DEFAULT_OVERRIDE_DURATION_MINUTES,
        )
        try:
            minutes = int(configured)
        except (TypeError, ValueError):
            minutes = DEFAULT_OVERRIDE_DURATION_MINUTES
        return max(
            MIN_OVERRIDE_DURATION_MINUTES,
            min(MAX_OVERRIDE_DURATION_MINUTES, minutes),
        )

    async def _async_resolve_actor_id(self) -> str:
        if self._actor_id is not None:
            return self._actor_id

        location_id = self.location_entry.get("id")
        if not isinstance(location_id, int):
            raise CatchSolarApiError("Catch Solar location is not available")
        serial_number = (self.primary_device_entry or {}).get("serial_number")
        actors = await self._api.async_get_actors(location_id)
        actor_id = resolve_relay_actor_id(actors, serial_number)
        if actor_id is None:
            raise CatchSolarApiError(
                f"No controllable relay actor found for serial {serial_number}"
            )
        self._actor_id = actor_id
        return actor_id

    def _schedule_expiry(self) -> None:
        self._cancel_expiry()
        if self._expires_at is None or self.hass is None:
            return
        delay = max(0.0, (self._expires_at - dt_util.utcnow()).total_seconds())
        self._unsub_expiry = async_call_later(self.hass, delay, self._handle_expiry)

    def _cancel_expiry(self) -> None:
        if self._unsub_expiry is not None:
            self._unsub_expiry()
            self._unsub_expiry = None

    @callback
    def _handle_expiry(self, _now) -> None:
        self._unsub_expiry = None
        self._option = OVERRIDE_MODE_AUTO
        self._expires_at = None
        self.async_write_ha_state()


def _parse_expiry(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None or parsed.tzinfo is None:
        return None
    return parsed
