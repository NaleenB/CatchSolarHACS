from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CatchSolarApiAuthError, CatchSolarApiClient, CatchSolarApiError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_ENABLE_POWER_DATA,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_PASSWORD,
    CONF_PRIMARY_LOAD_LABEL,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_POWER_DATA,
    DEFAULT_PRIMARY_LOAD_LABEL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)


class CatchSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._account_id: int | None = None
        self._locations: list[dict[str, Any]] = []
        self._username: str = ""
        self._password: str = ""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = str(user_input[CONF_USERNAME])
            self._password = str(user_input[CONF_PASSWORD])
            api = CatchSolarApiClient(
                async_get_clientsession(self.hass),
                self._username,
                self._password,
            )
            try:
                login = await api.async_login()
                self._account_id = int(login["id"])
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
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_location(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_id = int(user_input["location_id"])
            location = next(
                (item for item in self._locations if int(item.get("id")) == selected_id),
                None,
            )
            if location is None:
                errors["base"] = "invalid_location"
            else:
                return await self._async_create_location_entry(location)

        options = {str(item["id"]): item.get("name") or str(item["id"]) for item in self._locations}
        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema({vol.Required("location_id"): vol.In(options)}),
            errors=errors,
        )

    async def _async_create_location_entry(self, location: dict[str, Any]):
        location_id = int(location["id"])
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
                CONF_ENABLE_POWER_DATA: DEFAULT_ENABLE_POWER_DATA,
                CONF_PRIMARY_LOAD_LABEL: DEFAULT_PRIMARY_LOAD_LABEL,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._username = str(entry_data.get(CONF_USERNAME, ""))
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_unsuccessful")

        if user_input is not None:
            self._username = str(user_input[CONF_USERNAME])
            self._password = str(user_input[CONF_PASSWORD])
            api = CatchSolarApiClient(
                async_get_clientsession(self.hass),
                self._username,
                self._password,
            )
            try:
                await api.async_login()
            except CatchSolarApiAuthError:
                errors["base"] = "invalid_auth"
            except CatchSolarApiError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._username): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return CatchSolarOptionsFlow(config_entry)


class CatchSolarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60)),
                    vol.Required(
                        CONF_ENABLE_POWER_DATA,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_POWER_DATA, DEFAULT_ENABLE_POWER_DATA
                        ),
                    ): bool,
                    vol.Required(
                        CONF_PRIMARY_LOAD_LABEL,
                        default=self.config_entry.options.get(
                            CONF_PRIMARY_LOAD_LABEL, DEFAULT_PRIMARY_LOAD_LABEL
                        ),
                    ): str,
                }
            ),
        )
