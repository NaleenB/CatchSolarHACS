from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from custom_components.catchsolar.config_flow import CatchSolarConfigFlow
from custom_components.catchsolar.const import (
    CONF_ACCOUNT_ID,
    CONF_ENABLE_POWER_DATA,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_PASSWORD,
    CONF_PRIMARY_LOAD_LABEL,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_POWER_DATA,
    DEFAULT_PRIMARY_LOAD_LABEL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)


def _attach_hass(flow: CatchSolarConfigFlow, hass) -> CatchSolarConfigFlow:
    flow.hass = hass
    flow.context = {}
    return flow


async def test_user_flow_single_location_creates_entry_with_default_options(hass) -> None:
    flow = _attach_hass(CatchSolarConfigFlow(), hass)
    login_response = {"id": 42}
    locations_response = [{"id": 1234, "name": "Home"}]

    with (
        patch(
            "custom_components.catchsolar.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.catchsolar.config_flow.CatchSolarApiClient",
        ) as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value=login_response)
        client.async_get_locations = AsyncMock(return_value=locations_response)

        result = await flow.async_step_user(
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "secret"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["data"] == {
        CONF_USERNAME: "user@example.com",
        CONF_PASSWORD: "secret",
        CONF_ACCOUNT_ID: 42,
        CONF_LOCATION_ID: 1234,
        CONF_LOCATION_NAME: "Home",
    }
    assert result["options"] == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_SECONDS,
        CONF_ENABLE_POWER_DATA: DEFAULT_ENABLE_POWER_DATA,
        CONF_PRIMARY_LOAD_LABEL: DEFAULT_PRIMARY_LOAD_LABEL,
    }


async def test_options_flow_returns_user_values(hass) -> None:
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain="catchsolar",
        title="Home",
        data={},
        options={
            CONF_SCAN_INTERVAL: 900,
            CONF_ENABLE_POWER_DATA: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
        },
        source="user",
        entry_id="test-entry",
        discovery_keys={},
        subentries_data={},
    )
    flow = CatchSolarConfigFlow.async_get_options_flow(entry)
    flow.hass = hass

    result = await flow.async_step_init(
        {
            CONF_SCAN_INTERVAL: 300,
            CONF_ENABLE_POWER_DATA: True,
            CONF_PRIMARY_LOAD_LABEL: "Pool Pump",
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 300,
        CONF_ENABLE_POWER_DATA: True,
        CONF_PRIMARY_LOAD_LABEL: "Pool Pump",
    }


async def test_options_flow_init_form_uses_existing_defaults(hass) -> None:
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain="catchsolar",
        title="Home",
        data={},
        options={
            CONF_SCAN_INTERVAL: 900,
            CONF_ENABLE_POWER_DATA: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
        },
        source="user",
        entry_id="test-entry",
        discovery_keys={},
        subentries_data={},
    )
    flow = CatchSolarConfigFlow.async_get_options_flow(entry)
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] is FlowResultType.FORM
    assert flow._config_entry is entry
