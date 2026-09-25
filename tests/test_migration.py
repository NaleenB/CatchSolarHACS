from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.catchsolar import async_migrate_entry
from custom_components.catchsolar.config_flow import CatchSolarConfigFlow
from custom_components.catchsolar.const import DOMAIN


def _entity_entry(
    entity_id: str,
    unique_id: str,
    *,
    domain: str = "sensor",
    platform: str = "catchsolar",
) -> SimpleNamespace:
    return SimpleNamespace(
        entity_id=entity_id,
        unique_id=unique_id,
        domain=domain,
        platform=platform,
    )


@pytest.mark.asyncio
async def test_migration_removes_data24_option_and_entities() -> None:
    entry = SimpleNamespace(
        version=1,
        options={"enable_power_data": True, "enable_live_data": True},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.entities = {}
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
        version=4,
    )


@pytest.mark.asyncio
async def test_migration_renames_active_control_entity_from_version_two() -> None:
    entry = SimpleNamespace(
        version=2,
        options={"enable_live_data": True},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.entities = {}
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
        version=4,
    )


@pytest.mark.asyncio
async def test_migration_removes_retired_live_entities_and_nothing_else() -> None:
    """Version 3 → 4 deletes the retired live sensors, and only those."""
    entry = SimpleNamespace(
        version=3,
        options={"enable_live_data": True},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.entities = {
        # Retired: channel power sensor from a nameless channel.
        "sensor.dup_mains": _entity_entry("sensor.dup_mains", "8382_channel_MAINS:_live_power"),
        "sensor.dup_solar": _entity_entry("sensor.dup_solar", "8382_channel_SOLAR:_live_power"),
        # Retired: actor power sensor.
        "sensor.actor_power": _entity_entry(
            "sensor.actor_power", "8382_actor_GLD.SR.3649_live_power"
        ),
        # A named channel is a real entity and must survive.
        "sensor.named_channel": _entity_entry(
            "sensor.named_channel", "8382_channel_LOAD:Hot Water_live_power"
        ),
        # Actor state and SoC are still produced and must survive.
        "sensor.actor_state": _entity_entry(
            "sensor.actor_state", "8382_actor_GLD.SR.3649_live_state"
        ),
        "sensor.actor_soc": _entity_entry("sensor.actor_soc", "8382_actor_battery-1_live_soc"),
        # Site-level power sensors must survive.
        "sensor.site_mains": _entity_entry("sensor.site_mains", "8382_live_mains_power"),
        # Same suffix but a different location.
        "sensor.other_location": _entity_entry(
            "sensor.other_location", "9999_channel_MAINS:_live_power"
        ),
        "sensor.other_location_actor": _entity_entry(
            "sensor.other_location_actor", "9999_actor_GLD.SR.3649_live_power"
        ),
        # Same unique id but not our platform / not a sensor.
        "sensor.other_platform": _entity_entry(
            "sensor.other_platform", "8382_channel_MAINS:_live_power", platform="other"
        ),
        "binary_sensor.dup": _entity_entry(
            "binary_sensor.dup", "8382_channel_MAINS:_live_power", domain="binary_sensor"
        ),
    }
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get", return_value=registry):
        assert await async_migrate_entry(hass, entry) is True

    removed = sorted(call.args[0] for call in registry.async_remove.call_args_list)
    assert removed == ["sensor.actor_power", "sensor.dup_mains", "sensor.dup_solar"]
    # The 3.x entity/rename cleanup must not re-run for a version 3 entry.
    registry.async_get_entity_id.assert_not_called()
    registry.async_update_entity.assert_not_called()
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={"enable_live_data": True},
        version=4,
    )


@pytest.mark.asyncio
async def test_migration_is_a_no_op_at_the_current_version() -> None:
    entry = SimpleNamespace(
        version=4,
        options={"enable_live_data": True},
        data={"location_id": 8382},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get") as registry_get:
        assert await async_migrate_entry(hass, entry) is True

    registry_get.assert_not_called()
    hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_config_flow_version_matches_the_migration_target() -> None:
    """Home Assistant only migrates when the stored version differs from VERSION.

    If ``CatchSolarConfigFlow.VERSION`` lags the version ``async_migrate_entry``
    writes, an already-current entry is never migrated and every cleanup below
    that version is silently skipped.
    """
    entry = SimpleNamespace(
        version=1,
        options={},
        data={"location_id": 8382},
    )
    registry = Mock()
    registry.entities = {}
    registry.async_get_entity_id.return_value = None
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=Mock()),
    )

    with patch("custom_components.catchsolar.er.async_get", return_value=registry):
        assert await async_migrate_entry(hass, entry) is True

    migrated_to = hass.config_entries.async_update_entry.call_args.kwargs["version"]
    assert migrated_to == CatchSolarConfigFlow.VERSION


@pytest.mark.asyncio
async def test_home_assistant_dispatcher_runs_the_migration(
    hass, enable_custom_integrations
) -> None:
    """Exercise Home Assistant's real migration dispatcher, not just our function.

    ``ConfigEntry.async_migrate`` returns early when the stored entry version
    equals the flow handler's ``VERSION``, so calling ``async_migrate_entry``
    directly cannot catch a version mismatch. This goes through the dispatcher.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"location_id": 8382},
        options={"enable_live_data": True},
    )
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    stale_channel = registry.async_get_or_create(
        "sensor", DOMAIN, "8382_channel_MAINS:_live_power", config_entry=entry
    )
    stale_actor_power = registry.async_get_or_create(
        "sensor", DOMAIN, "8382_actor_GLD.SR.3649_live_power", config_entry=entry
    )
    kept = registry.async_get_or_create(
        "sensor", DOMAIN, "8382_actor_GLD.SR.3649_live_state", config_entry=entry
    )

    assert await entry.async_migrate(hass) is True
    await hass.async_block_till_done()

    assert entry.version == CatchSolarConfigFlow.VERSION
    assert registry.async_get(stale_channel.entity_id) is None
    assert registry.async_get(stale_actor_power.entity_id) is None
    assert registry.async_get(kept.entity_id) is not None
