from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.catchsolar.api import CatchSolarApiAuthError, CatchSolarApiError
from custom_components.catchsolar.const import (
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
)
from custom_components.catchsolar.coordinator import CatchSolarDataUpdateCoordinator


@pytest.mark.asyncio
async def test_coordinator_raises_auth_failed_for_auth_errors(hass) -> None:
    api = AsyncMock()
    api.async_get_devices.side_effect = CatchSolarApiAuthError("bad credentials")
    runtime_tracker = AsyncMock()
    coordinator = CatchSolarDataUpdateCoordinator(
        hass,
        api,
        {CONF_LOCATION_ID: 1234, CONF_LOCATION_NAME: "Home"},
        runtime_tracker,
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_for_other_api_errors(hass) -> None:
    api = AsyncMock()
    api.async_get_devices.side_effect = CatchSolarApiError("timeout")
    runtime_tracker = AsyncMock()
    coordinator = CatchSolarDataUpdateCoordinator(
        hass,
        api,
        {CONF_LOCATION_ID: 1234, CONF_LOCATION_NAME: "Home"},
        runtime_tracker,
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_uses_configured_location_without_polling_locations(hass) -> None:
    api = AsyncMock()
    api.async_get_devices.return_value = [
        {
            "online": 1,
            "loadState": 1,
            "device": {"id": 123, "controllingLoad": 1},
        }
    ]
    snapshot = Mock(as_dict=Mock(return_value={"primary_load_on": True}))
    runtime_tracker = AsyncMock()
    runtime_tracker.async_process.return_value = snapshot
    coordinator = CatchSolarDataUpdateCoordinator(
        hass,
        api,
        {
            CONF_LOCATION_ID: 1234,
            CONF_LOCATION_NAME: "Home",
        },
        runtime_tracker,
    )

    data = await coordinator._async_update_data()

    assert data["location"] == {"id": 1234, "name": "Home"}
    assert data["devices"][0]["load_state"] == 1
    api.async_get_locations.assert_not_awaited()
