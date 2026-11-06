from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.catchsolar.api import CatchSolarApiError
from custom_components.catchsolar.const import (
    OVERRIDE_MODE_AUTO,
    OVERRIDE_MODE_OFF,
    OVERRIDE_MODE_ON,
)
from custom_components.catchsolar.select import (
    CatchSolarPrimaryLoadControlSelect,
    async_setup_entry,
)


def _coordinator(*, actors=None, duration=90, load_state=0):
    api = SimpleNamespace(
        async_get_actors=AsyncMock(return_value=actors or ["SR.88888", "GLD.SR.88888"]),
        async_save_override=AsyncMock(return_value=None),
        async_remove_override=AsyncMock(return_value=None),
    )
    return SimpleNamespace(
        data={
            "location": {"id": 99999, "name": "Home"},
            "primary_device_id": 88888,
            "devices": [
                {
                    "id": 88888,
                    "device_name": "Water Heater",
                    "serial_number": "88888",
                    "device_type": "SR",
                    "load_state": load_state,
                    "online": 1,
                }
            ],
        },
        config={"primary_load_label": "Water Heater", "override_duration": duration},
        api=api,
        last_update_success=True,
        async_request_refresh=AsyncMock(),
    )


def _entity(coordinator):
    entity = CatchSolarPrimaryLoadControlSelect(coordinator, SimpleNamespace())
    entity.async_write_ha_state = Mock()
    return entity


async def test_setup_adds_one_primary_load_control(hass) -> None:
    coordinator = _coordinator()
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=coordinator),
    )
    added = []

    await async_setup_entry(hass, entry, added.extend)

    assert len(added) == 1
    assert isinstance(added[0], CatchSolarPrimaryLoadControlSelect)


async def test_select_on_writes_timed_override() -> None:
    coordinator = _coordinator(duration=90)
    entity = _entity(coordinator)
    assert entity.current_option == OVERRIDE_MODE_AUTO

    await entity.async_select_option(OVERRIDE_MODE_ON)

    coordinator.api.async_get_actors.assert_awaited_once_with(99999)
    coordinator.api.async_save_override.assert_awaited_once_with(
        99999, "GLD.SR.88888", OVERRIDE_MODE_ON, 90
    )
    assert entity.current_option == OVERRIDE_MODE_ON
    assert entity.extra_state_attributes["override_expires_at"] is not None
    coordinator.async_request_refresh.assert_awaited_once()


async def test_select_off_writes_timed_override_and_clamps_duration() -> None:
    coordinator = _coordinator(duration=9999)
    entity = _entity(coordinator)

    await entity.async_select_option(OVERRIDE_MODE_OFF)

    coordinator.api.async_save_override.assert_awaited_once_with(
        99999, "GLD.SR.88888", OVERRIDE_MODE_OFF, 480
    )
    assert entity.current_option == OVERRIDE_MODE_OFF


async def test_select_auto_removes_override() -> None:
    coordinator = _coordinator()
    entity = _entity(coordinator)
    entity._option = OVERRIDE_MODE_ON

    await entity.async_select_option(OVERRIDE_MODE_AUTO)

    coordinator.api.async_remove_override.assert_awaited_once_with(
        99999, "GLD.SR.88888"
    )
    assert entity.current_option == OVERRIDE_MODE_AUTO
    assert entity.extra_state_attributes["override_expires_at"] is None


async def test_select_rejects_unknown_mode() -> None:
    entity = _entity(_coordinator())

    with pytest.raises(HomeAssistantError, match="Unsupported"):
        await entity.async_select_option("heat")


async def test_select_reports_missing_relay_actor() -> None:
    coordinator = _coordinator(actors=["SR.11111"])
    entity = _entity(coordinator)

    with pytest.raises(HomeAssistantError, match="No controllable relay"):
        await entity.async_select_option(OVERRIDE_MODE_ON)

    coordinator.api.async_save_override.assert_not_awaited()


async def test_select_reports_api_failure() -> None:
    coordinator = _coordinator()
    coordinator.api.async_save_override.side_effect = CatchSolarApiError("boom")
    entity = _entity(coordinator)

    with pytest.raises(HomeAssistantError, match="boom"):
        await entity.async_select_option(OVERRIDE_MODE_ON)

    assert entity.current_option == OVERRIDE_MODE_AUTO


async def test_sync_reads_active_override_from_catch() -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    coordinator = _coordinator()
    expires = dt_util.utcnow() + timedelta(minutes=30)
    coordinator.api.async_get_override_state = AsyncMock(
        return_value={"mode": OVERRIDE_MODE_ON, "expires_at": expires}
    )
    entity = _entity(coordinator)

    await entity._async_sync_override_state()

    coordinator.api.async_get_override_state.assert_awaited_once_with(
        99999, "GLD.SR.88888"
    )
    assert entity.current_option == OVERRIDE_MODE_ON


async def test_sync_clears_expired_override() -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    coordinator = _coordinator()
    coordinator.api.async_get_override_state = AsyncMock(
        return_value={
            "mode": OVERRIDE_MODE_OFF,
            "expires_at": dt_util.utcnow() - timedelta(minutes=1),
        }
    )
    entity = _entity(coordinator)
    entity._option = OVERRIDE_MODE_OFF

    await entity._async_sync_override_state()

    assert entity.current_option == OVERRIDE_MODE_AUTO
    assert entity.extra_state_attributes["override_expires_at"] is None
