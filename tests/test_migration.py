from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar import async_migrate_entry


@pytest.mark.asyncio
async def test_migration_removes_data24_option_and_entities() -> None:
    entry = SimpleNamespace(
        version=1,
        options={"enable_power_data": True, "enable_live_data": True},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.async_get_entity_id.side_effect = [
        "sensor.old_solar",
        "sensor.old_consumption",
        "sensor.old_grid",
        "sensor.old_undefined_channel",
    ]
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get", return_value=registry):
        assert await async_migrate_entry(hass, entry) is True

    assert registry.async_remove.call_count == 4
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={"enable_live_data": True},
        version=2,
    )
