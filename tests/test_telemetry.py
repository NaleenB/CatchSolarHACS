from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.catchsolar.telemetry import (
    CatchSolarDailyEnergyCoordinator,
    CatchSolarLiveClient,
    CatchSolarLiveCoordinator,
)


def _load_live_fixture() -> dict:
    return json.loads((Path(__file__).parent / "fixtures" / "live_event.json").read_text())


class _FakeSocket:
    def __init__(self, wait_callback=None, connect_error: Exception | None = None) -> None:
        self.handlers = {}
        self.wait_callback = wait_callback
        self.connect_error = connect_error
        self.connect_args = None
        self.disconnect_called = False

    def on(self, name):
        def register(handler):
            self.handlers[name] = handler
            return handler

        return register

    def event(self, handler):
        self.handlers[handler.__name__] = handler
        return handler

    async def connect(self, *args, **kwargs):
        self.connect_args = (args, kwargs)
        if self.connect_error is not None:
            raise self.connect_error

    async def wait(self):
        if self.wait_callback is not None:
            await self.wait_callback(self)

    async def disconnect(self):
        self.disconnect_called = True


@pytest.mark.asyncio
async def test_daily_energy_coordinator_parses_supported_meters(hass) -> None:
    api = AsyncMock()
    api.async_get_daily_energy.return_value = {
        "success": True,
        "result": {
            "xAxis": ["13-08-2026"],
            "seriesList": [
                {"name": "Solar", "totalWh": 12345, "dataWh": [12345]},
                {"name": "Export", "totalWh": -2345, "dataWh": [-2345]},
                {"name": "Import", "totalWh": 456, "dataWh": [456]},
                {
                    "name": "Total Consumption",
                    "totalWh": 10456,
                    "dataWh": [10456],
                },
                {"name": "Consumed Solar", "totalWh": 10000, "dataWh": [10000]},
            ],
        },
    }
    coordinator = CatchSolarDailyEnergyCoordinator(
        hass,
        api,
        {"location_id": 99999, "location_name": "Home"},
    )

    assert coordinator.update_interval == timedelta(seconds=300)

    result = await coordinator._async_update_data()

    assert result["series"]["solar_yield_energy"] == 12.345
    assert result["series"]["grid_export_energy"] == 2.345
    assert result["location"] == {"id": 99999, "name": "Home"}
    request = api.async_get_daily_energy.await_args.args
    assert request[0] == 99999
    assert request[1].endswith("Z")
    assert request[2].endswith("Z")


@pytest.mark.asyncio
async def test_live_coordinator_updates_from_event_and_can_shutdown(hass) -> None:
    coordinator = CatchSolarLiveCoordinator(
        hass,
        {"location_id": 99999, "location_name": "Home"},
    )

    await coordinator.async_handle_event(
        {
            "mainsPWR": -250,
            "solarPWR": 4200,
            "housePWR": 3950,
            "batteryPWR": 0,
            "channels": [],
            "controllable": {},
        }
    )

    assert coordinator.data["site_power"]["mains_power"] == -250
    assert coordinator.data["location"] == {"id": 99999, "name": "Home"}
    assert coordinator.data["last_event_at"] is not None
    assert coordinator.last_update_success is True

    await coordinator.async_shutdown()
    assert coordinator._stale_handle is None


@pytest.mark.asyncio
async def test_live_coordinator_throttles_publication_to_latest_event(hass) -> None:
    coordinator = CatchSolarLiveCoordinator(
        hass,
        {"location_id": 99999, "location_name": "Home"},
    )

    await coordinator.async_handle_event({"mainsPWR": -100})
    first_published_at = coordinator.data["last_published_at"]
    await coordinator.async_handle_event({"mainsPWR": -200})

    assert coordinator.data["site_power"]["mains_power"] == -100
    assert coordinator._pending_data is not None
    assert coordinator._publish_handle is not None

    coordinator._cancel_publish_handle()
    coordinator._publish_pending()

    assert coordinator.data["site_power"]["mains_power"] == -200
    assert coordinator.data["last_published_at"] >= first_published_at
    assert coordinator._pending_data is None

    await coordinator.async_shutdown()
    assert coordinator._publish_handle is None


@pytest.mark.asyncio
async def test_live_client_refreshes_token_after_reconnect(hass) -> None:
    coordinator = CatchSolarLiveCoordinator(
        hass,
        {"location_id": 99999, "location_name": "Home"},
    )
    api = AsyncMock()
    api.async_get_access_token.side_effect = ["token-1", "token-2"]
    client = CatchSolarLiveClient(
        hass,
        api,
        AsyncMock(),
        99999,
        coordinator,
    )

    async def first_wait(socket):
        await socket.handlers["event"](_load_live_fixture())

    async def second_wait(socket):
        await socket.handlers["event"](_load_live_fixture())
        client._stopping = True

    sockets = [_FakeSocket(first_wait), _FakeSocket(second_wait)]
    with (
        patch("custom_components.catchsolar.telemetry.socketio.AsyncClient", side_effect=sockets),
        patch("custom_components.catchsolar.telemetry.asyncio.sleep", new=AsyncMock()),
    ):
        await client._async_connection_loop()

    assert api.async_get_access_token.await_args_list[0].args == ()
    assert api.async_get_access_token.await_args_list[0].kwargs == {"refresh": False}
    assert api.async_get_access_token.await_args_list[1].kwargs == {"refresh": True}
    assert sockets[0].connect_args[1]["auth"] == {"token": "token-1", "locationId": 99999}
    assert sockets[1].connect_args[1]["auth"] == {"token": "token-2", "locationId": 99999}
    assert sockets[0].disconnect_called is True
    assert sockets[1].disconnect_called is True
    assert coordinator.data["site_power"]["solar_power"] == 4200.0

    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_live_client_reports_connect_failure_and_applies_backoff(hass) -> None:
    coordinator = CatchSolarLiveCoordinator(
        hass,
        {"location_id": 99999, "location_name": "Home"},
    )
    api = AsyncMock()
    api.async_get_access_token.return_value = "token-1"
    client = CatchSolarLiveClient(
        hass,
        api,
        AsyncMock(),
        99999,
        coordinator,
    )
    delays = []

    async def sleep(delay):
        delays.append(delay)
        client._stopping = True

    socket = _FakeSocket(connect_error=RuntimeError("connection refused"))
    with (
        patch("custom_components.catchsolar.telemetry.socketio.AsyncClient", return_value=socket),
        patch("custom_components.catchsolar.telemetry.asyncio.sleep", side_effect=sleep),
    ):
        await client._async_connection_loop()

    assert delays == [5]
    assert coordinator.last_update_success is False
    assert socket.disconnect_called is True

    await coordinator.async_shutdown()
