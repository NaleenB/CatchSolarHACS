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
        "sensor.old_export_limit",
    ]
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get", return_value=registry):
        assert await async_migrate_entry(hass, entry) is True

    assert registry.async_remove.call_count == 4
    registry.async_update_entity.assert_called_once_with(
        "sensor.old_export_limit",
        new_unique_id="8382_live_active_control",
    )
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={"enable_live_data": True},
        version=3,
    )


@pytest.mark.asyncio
async def test_migration_renames_active_control_entity_from_version_two() -> None:
    entry = SimpleNamespace(
        version=2,
        options={"enable_live_data": True},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.async_get_entity_id.side_effect = [None, None, None, None, "sensor.old_export_limit"]
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get", return_value=registry):
        assert await async_migrate_entry(hass, entry) is True

    registry.async_update_entity.assert_called_once_with(
        "sensor.old_export_limit",
        new_unique_id="8382_live_active_control",
    )
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={"enable_live_data": True},
        version=3,
    )
