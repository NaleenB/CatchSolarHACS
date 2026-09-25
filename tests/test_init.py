from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.catchsolar import (
    _async_register_location_device,
    async_remove_config_entry_device,
    async_remove_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.catchsolar.const import DOMAIN


@pytest.mark.asyncio
async def test_remove_entry_deletes_runtime_store_from_loaded_tracker(hass) -> None:
    runtime_tracker = AsyncMock()

    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(runtime_tracker=runtime_tracker),
    )
    await async_remove_entry(hass, entry)

    runtime_tracker.async_delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_unload_entry_shuts_down_daily_energy_coordinator(hass) -> None:
    live_client = AsyncMock()
    daily_energy_coordinator = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = SimpleNamespace(
        entry_id="entry-1",
        runtime_data=SimpleNamespace(
            live_client=live_client,
            daily_energy_coordinator=daily_energy_coordinator,
        ),
    )
    assert await async_unload_entry(hass, entry) is True

    live_client.async_stop.assert_awaited_once()
    daily_energy_coordinator.async_shutdown.assert_awaited_once()
    assert entry.runtime_data is not None


@pytest.mark.asyncio
async def test_setup_failure_shuts_down_daily_energy_coordinator(hass) -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            "username": "user@example.com",
            "password": "secret",
            "location_id": 8382,
            "location_name": "Home",
        },
        options={"enable_live_data": True, "enable_daily_energy": True},
        async_on_unload=Mock(),
        runtime_data=None,
    )
    runtime_tracker = AsyncMock()
    core_coordinator = AsyncMock()
    core_coordinator.data = {"location": {"id": 8382, "name": "Home"}}
    daily_energy_coordinator = AsyncMock()
    live_coordinator = Mock()
    live_client = AsyncMock()
    device_registry = Mock()
    device_registry.async_get_or_create.return_value = SimpleNamespace(id="location-device-id")
    hass.config_entries.async_forward_entry_setups = AsyncMock(
        side_effect=RuntimeError("platform setup failed")
    )

    with (
        patch("custom_components.catchsolar.async_get_clientsession", return_value=object()),
        patch("custom_components.catchsolar.CatchSolarApiClient"),
        patch(
            "custom_components.catchsolar.PrimaryLoadRuntimeTracker",
            return_value=runtime_tracker,
        ),
        patch(
            "custom_components.catchsolar.CatchSolarDataUpdateCoordinator",
            return_value=core_coordinator,
        ),
        patch(
            "custom_components.catchsolar.CatchSolarDailyEnergyCoordinator",
            return_value=daily_energy_coordinator,
        ),
        patch(
            "custom_components.catchsolar.CatchSolarLiveCoordinator",
            return_value=live_coordinator,
        ),
        patch(
            "custom_components.catchsolar.CatchSolarLiveClient",
            return_value=live_client,
        ),
        patch("custom_components.catchsolar.dr.async_get", return_value=device_registry),
    ):
        with pytest.raises(RuntimeError, match="platform setup failed"):
            await async_setup_entry(hass, entry)

    live_client.async_start.assert_awaited_once()
    live_client.async_stop.assert_awaited_once()
    daily_energy_coordinator.async_shutdown.assert_awaited_once()
    assert entry.runtime_data is not None
    # The parent device is registered up-front and its registry id is shared
    # with the live coordinator so actor devices can link to it.
    device_registry.async_get_or_create.assert_called_once()
    assert core_coordinator.location_device_id == "location-device-id"
    assert live_coordinator.location_device_id == "location-device-id"


@pytest.mark.asyncio
async def test_register_location_device_returns_registry_id() -> None:
    device_registry = Mock()
    device_registry.async_get_or_create.return_value = SimpleNamespace(id="dev-1")
    hass = SimpleNamespace()

    with patch("custom_components.catchsolar.dr.async_get", return_value=device_registry):
        result = _async_register_location_device(
            hass, SimpleNamespace(entry_id="entry-1"), {"id": 8382, "name": "Home"}
        )

    assert result == "dev-1"
    assert device_registry.async_get_or_create.call_args.kwargs["identifiers"] == {
        (DOMAIN, "location_8382")
    }
    assert (
        device_registry.async_get_or_create.call_args.kwargs["name"]
        == "Home (Catch Solar Location 8382)"
    )


@pytest.mark.asyncio
async def test_register_location_device_skips_missing_location_id() -> None:
    hass = SimpleNamespace()

    with patch("custom_components.catchsolar.dr.async_get") as registry_get:
        result = _async_register_location_device(hass, SimpleNamespace(entry_id="entry-1"), {})

    assert result is None
    registry_get.assert_not_called()


@pytest.mark.asyncio
async def test_remove_config_entry_device_refuses_known_device(hass) -> None:
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(
                data={
                    "location": {"id": 8382},
                    "devices": [{"id": 9310}],
                }
            ),
            live_coordinator=None,
        )
    )
    device_entry = SimpleNamespace(identifiers={(DOMAIN, "device_9310")})

    assert await async_remove_config_entry_device(hass, entry, device_entry) is False


@pytest.mark.asyncio
async def test_remove_config_entry_device_allows_stale_device(hass) -> None:
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data={"location": {"id": 8382}, "devices": []}),
            live_coordinator=None,
        )
    )
    device_entry = SimpleNamespace(identifiers={(DOMAIN, "device_9310")})

    assert await async_remove_config_entry_device(hass, entry, device_entry) is True
