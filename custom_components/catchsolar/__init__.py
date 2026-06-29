from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CatchSolarApiClient
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import CatchSolarDataUpdateCoordinator
from .runtime import PrimaryLoadRuntimeTracker


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = CatchSolarApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    runtime_tracker = PrimaryLoadRuntimeTracker(hass, entry.entry_id)
    await runtime_tracker.async_load()

    coordinator = CatchSolarDataUpdateCoordinator(
        hass,
        api,
        {**entry.data, **entry.options},
        runtime_tracker,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "runtime_tracker": runtime_tracker,
    }
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    runtime_tracker = runtime_data.get("runtime_tracker")
    if runtime_tracker is None:
        runtime_tracker = PrimaryLoadRuntimeTracker(hass, entry.entry_id)
        await runtime_tracker.async_load()
    await runtime_tracker.async_delete()


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    identifiers = {identifier for identifier in device_entry.identifiers if identifier[0] == DOMAIN}
    return bool(identifiers)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
