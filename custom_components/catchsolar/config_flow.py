from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CatchSolarApiAuthError, CatchSolarApiClient, CatchSolarApiError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_ENABLE_DAILY_ENERGY,
    CONF_ENABLE_LIVE_DATA,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_PASSWORD,
    CONF_PRIMARY_DEVICE_ID,
    CONF_PRIMARY_LOAD_LABEL,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_DAILY_ENERGY,
    DEFAULT_ENABLE_LIVE_DATA,
    DEFAULT_PRIMARY_LOAD_LABEL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)


class CatchSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    def __init__(self) -> None:
        self._account_id: int | None = None
        self._locations: list[dict[str, Any]] = []
        self._username = ""
        self._password = ""

    def _api_client(self, username: str, password: str) -> CatchSolarApiClient:
        return CatchSolarApiClient(async_get_clientsession(self.hass), username, password)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = str(user_input[CONF_USERNAME])
            self._password = str(user_input[CONF_PASSWORD])
            api = self._api_client(self._username, self._password)
            try:
                login = await api.async_login()
                self._account_id = _safe_int(login.get("id"))
                if self._account_id is None:
                    raise CatchSolarApiError("Login response did not contain an account id")
                self._locations = await api.async_get_locations()
                if not self._locations:
                    errors["base"] = "no_locations"
                elif len(self._locations) == 1:
                    return await self._async_create_location_entry(self._locations[0])
                else:
                    return await self.async_step_location()
            except CatchSolarApiAuthError:
                errors["base"] = "invalid_auth"
            except CatchSolarApiError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): selector.TextSelector(),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_location(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_id = _safe_int(user_input.get("location_id"))
            location = next(
                (item for item in self._locations if _safe_int(item.get("id")) == selected_id),
                None,
            )
            if location is None:
                errors["base"] = "invalid_location"
            else:
                return await self._async_create_location_entry(location)

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": str(item["id"]),
                                    "label": item.get("name") or str(item["id"]),
                                }
                                for item in self._locations
                                if _safe_int(item.get("id")) is not None
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def _async_create_location_entry(self, location: dict[str, Any]):
        location_id = _safe_int(location.get("id"))
        if location_id is None or self._account_id is None:
            return self.async_abort(reason="invalid_location")
        unique_id = f"{self._account_id}:{location_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location.get("name") or f"Catch Solar {location_id}",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_ACCOUNT_ID: self._account_id,
                CONF_LOCATION_ID: location_id,
                CONF_LOCATION_NAME: location.get("name"),
            },
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_SECONDS,
                CONF_ENABLE_LIVE_DATA: DEFAULT_ENABLE_LIVE_DATA,
                CONF_ENABLE_DAILY_ENERGY: DEFAULT_ENABLE_DAILY_ENERGY,
                CONF_PRIMARY_LOAD_LABEL: DEFAULT_PRIMARY_LOAD_LABEL,
            },
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            username = str(user_input[CONF_USERNAME])
            password = str(user_input[CONF_PASSWORD])
            api = self._api_client(username, password)
            try:
                login = await api.async_login()
                account_id = _safe_int(login.get("id"))
                locations = await api.async_get_locations()
                location_id = _safe_int(reauth_entry.data.get(CONF_LOCATION_ID))
                if account_id is None or location_id is None:
                    raise CatchSolarApiError("Reauthentication response was incomplete")
                if not any(_safe_int(item.get("id")) == location_id for item in locations):
                    errors["base"] = "location_not_found"
                else:
                    await self.async_set_unique_id(f"{account_id}:{location_id}")
                    self._abort_if_unique_id_mismatch(reason="wrong_account")
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data_updates={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_ACCOUNT_ID: account_id,
                        },
                    )
            except CatchSolarApiAuthError:
                errors["base"] = "invalid_auth"
            except CatchSolarApiError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reauth_entry.data.get(CONF_USERNAME, ""),
                    ): selector.TextSelector(),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            self._username = str(user_input[CONF_USERNAME])
            self._password = str(user_input[CONF_PASSWORD])
            api = self._api_client(self._username, self._password)
            try:
                login = await api.async_login()
                self._account_id = _safe_int(login.get("id"))
                self._locations = await api.async_get_locations()
                if self._account_id is None:
                    raise CatchSolarApiError("Login response did not contain an account id")
                if not self._locations:
                    errors["base"] = "no_locations"
                elif len(self._locations) == 1:
                    return await self._async_update_reconfigured_entry(self._locations[0])
                else:
                    return await self.async_step_reconfigure_location()
            except CatchSolarApiAuthError:
                errors["base"] = "invalid_auth"
            except CatchSolarApiError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, ""),
                    ): selector.TextSelector(),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure_location(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            location_id = _safe_int(user_input.get("location_id"))
            location = next(
                (item for item in self._locations if _safe_int(item.get("id")) == location_id),
                None,
            )
            if location is not None:
                return await self._async_update_reconfigured_entry(location)
            errors["base"] = "invalid_location"

        return self.async_show_form(
            step_id="reconfigure_location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": str(item["id"]),
                                    "label": item.get("name") or str(item["id"]),
                                }
                                for item in self._locations
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def _async_update_reconfigured_entry(self, location: dict[str, Any]):
        entry = self._get_reconfigure_entry()
        location_id = _safe_int(location.get("id"))
        if location_id is None or self._account_id is None:
            return self.async_abort(reason="invalid_location")
        await self.async_set_unique_id(f"{self._account_id}:{location_id}")
        self._abort_if_unique_id_mismatch(reason="wrong_account")
        options = dict(entry.options)
        if _safe_int(entry.data.get(CONF_LOCATION_ID)) != location_id:
            options.pop(CONF_PRIMARY_DEVICE_ID, None)
        return self.async_update_reload_and_abort(
            entry,
            data_updates={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_ACCOUNT_ID: self._account_id,
                CONF_LOCATION_ID: location_id,
                CONF_LOCATION_NAME: location.get("name"),
            },
            options=options,
            reason="reconfigure_successful",
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return CatchSolarOptionsFlow()


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class CatchSolarOptionsFlow(OptionsFlowWithReload):
    """Configure polling and optional telemetry without a second reload path."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        entry = self.config_entry
        errors: dict[str, str] = {}
        runtime_data = getattr(entry, "runtime_data", None)
        devices = []
        if runtime_data is not None:
            devices = [
                device
                for device in runtime_data.coordinator.data.get("devices", [])
                if _safe_int(device.get("controlling_load")) == 1
                and _safe_int(device.get("id")) is not None
            ]
        available_primary_ids = {_safe_int(device.get("id")) for device in devices} - {None}

        if user_input is not None:
            data = dict(user_input)
            primary_device_id = _safe_int(data.get(CONF_PRIMARY_DEVICE_ID))
            if primary_device_id is not None and primary_device_id not in available_primary_ids:
                errors["base"] = "invalid_primary_device"
            else:
                if primary_device_id is None:
                    data.pop(CONF_PRIMARY_DEVICE_ID, None)
                else:
                    data[CONF_PRIMARY_DEVICE_ID] = primary_device_id
                return self.async_create_entry(title="", data=data)

        current_primary = _safe_int(entry.options.get(CONF_PRIMARY_DEVICE_ID))
        primary_options = [{"value": "", "label": "Automatic primary relay"}]
        primary_options.extend(
            {
                "value": str(device["id"]),
                "label": device.get("device_name") or str(device["id"]),
            }
            for device in devices
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=60, max=86400, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_ENABLE_LIVE_DATA,
                        default=entry.options.get(CONF_ENABLE_LIVE_DATA, DEFAULT_ENABLE_LIVE_DATA),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_ENABLE_DAILY_ENERGY,
                        default=entry.options.get(
                            CONF_ENABLE_DAILY_ENERGY, DEFAULT_ENABLE_DAILY_ENERGY
                        ),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_PRIMARY_LOAD_LABEL,
                        default=entry.options.get(
                            CONF_PRIMARY_LOAD_LABEL, DEFAULT_PRIMARY_LOAD_LABEL
                        ),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_PRIMARY_DEVICE_ID,
                        default=str(current_primary) if current_primary is not None else "",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=primary_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )
