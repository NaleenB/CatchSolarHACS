from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.telemetry import (
    CatchSolarDailyEnergyCoordinator,
    CatchSolarLiveCoordinator,
)


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
