from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.catchsolar.api import CatchSolarApiAuthError, CatchSolarApiError
from custom_components.catchsolar.const import CONF_LOCATION_ID, CONF_LOCATION_NAME
from custom_components.catchsolar.coordinator import CatchSolarDataUpdateCoordinator


@pytest.mark.asyncio
async def test_coordinator_raises_auth_failed_for_auth_errors(hass) -> None:
    api = AsyncMock()
    api.async_get_locations.side_effect = CatchSolarApiAuthError("bad credentials")
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
    api.async_get_locations.side_effect = CatchSolarApiError("timeout")
    runtime_tracker = AsyncMock()
    coordinator = CatchSolarDataUpdateCoordinator(
        hass,
        api,
        {CONF_LOCATION_ID: 1234, CONF_LOCATION_NAME: "Home"},
        runtime_tracker,
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
