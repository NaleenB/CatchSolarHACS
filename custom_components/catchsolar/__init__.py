from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CatchSolarApiClient
from .const import (
    CONF_ENABLE_DAILY_ENERGY,
    CONF_ENABLE_LIVE_DATA,
    CONF_LOCATION_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_ENABLE_DAILY_ENERGY,
    DEFAULT_ENABLE_LIVE_DATA,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CatchSolarDataUpdateCoordinator
from .runtime import PrimaryLoadRuntimeTracker
from .supplemental import (
    CatchSolarDailyEnergyCoordinator,
    CatchSolarLiveClient,
    CatchSolarLiveCoordinator,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = CatchSolarApiClient(
        session,
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

    merged_config = {**entry.data, **entry.options}
    daily_energy_coordinator = None
    if merged_config.get(CONF_ENABLE_DAILY_ENERGY, DEFAULT_ENABLE_DAILY_ENERGY):
        daily_energy_coordinator = CatchSolarDailyEnergyCoordinator(hass, api, merged_config)
        await daily_energy_coordinator.async_refresh()

    live_coordinator = None
    live_client = None
    if merged_config.get(CONF_ENABLE_LIVE_DATA, DEFAULT_ENABLE_LIVE_DATA):
        live_coordinator = CatchSolarLiveCoordinator(hass, merged_config)
        live_client = CatchSolarLiveClient(
            api,
            session,
            int(merged_config[CONF_LOCATION_ID]),
            live_coordinator,
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "runtime_tracker": runtime_tracker,
        "daily_energy_coordinator": daily_energy_coordinator,
        "live_coordinator": live_coordinator,
        "live_client": live_client,
    }
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    if live_client is not None:
        await live_client.async_start()

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        if live_client is not None:
            await live_client.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    live_client = data.get("live_client")
    if live_client is not None:
        await live_client.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    elif live_client is not None:
        await live_client.async_start()
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Catch Solar component from configuration.yaml.

    This integration is configured exclusively through the config flow (UI).
    YAML-based setup is not supported — this stub exists so Home Assistant
    does not log a warning about a missing setup function.
    """
    return True
