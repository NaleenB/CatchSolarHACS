from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.const import DOMAIN
from custom_components.catchsolar.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_track_experimental_feature_state() -> None:
    core = SimpleNamespace(data={"devices": []})
    live = SimpleNamespace(data={"last_event_at": None}, last_update_success=False)
    entry = SimpleNamespace(
        entry_id="test-entry",
        data={"enable_live_data": True},
        options={"enable_daily_energy": False},
    )
    hass = SimpleNamespace(
        data={
            DOMAIN: {
                entry.entry_id: {
                    "coordinator": core,
                    "live_coordinator": live,
                    "daily_energy_coordinator": None,
                }
            }
        }
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["experimental_features"]["live_socketio_telemetry"] == {
        "introduced_in": "0.2.0",
        "option": "enable_live_data",
        "enabled": True,
        "loaded": True,
        "last_update_success": False,
    }
    assert result["experimental_features"]["daily_energy_meters"] == {
        "introduced_in": "0.2.0",
        "option": "enable_daily_energy",
        "enabled": False,
        "loaded": False,
        "last_update_success": None,
    }
