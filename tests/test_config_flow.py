from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.catchsolar.config_flow import CatchSolarConfigFlow
from custom_components.catchsolar.const import (
    CONF_ACCOUNT_ID,
    CONF_ENABLE_DAILY_ENERGY,
    CONF_ENABLE_LIVE_DATA,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_PASSWORD,
    CONF_PRIMARY_DEVICE_ID,
    CONF_PRIMARY_LOAD_LABEL,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENABLE_DAILY_ENERGY,
    DEFAULT_ENABLE_LIVE_DATA,
    DEFAULT_PRIMARY_LOAD_LABEL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)


def _attach_hass(flow: CatchSolarConfigFlow, hass) -> CatchSolarConfigFlow:
    flow.hass = hass
    flow.context = {}
    return flow


def _config_entry(**kwargs):
    parameters = inspect.signature(config_entries.ConfigEntry).parameters
    if "unique_id" in parameters:
        kwargs["unique_id"] = None
    if "subentries_data" in parameters:
        kwargs["subentries_data"] = {}
    return config_entries.ConfigEntry(**kwargs)


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
        CONF_ENABLE_LIVE_DATA: DEFAULT_ENABLE_LIVE_DATA,
        CONF_ENABLE_DAILY_ENERGY: DEFAULT_ENABLE_DAILY_ENERGY,
        CONF_PRIMARY_LOAD_LABEL: DEFAULT_PRIMARY_LOAD_LABEL,
    }


async def test_user_flow_rejects_malformed_account_id(hass) -> None:
    flow = _attach_hass(CatchSolarConfigFlow(), hass)

    with (
        patch(
            "custom_components.catchsolar.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.catchsolar.config_flow.CatchSolarApiClient",
        ) as client_cls,
    ):
        client_cls.return_value.async_login = AsyncMock(return_value={"id": "invalid"})

        result = await flow.async_step_user(
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "secret"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_returns_user_values(hass) -> None:
    entry = _config_entry(
        version=1,
        minor_version=1,
        domain="catchsolar",
        title="Home",
        data={},
        options={
            CONF_SCAN_INTERVAL: 900,
            CONF_ENABLE_LIVE_DATA: False,
            CONF_ENABLE_DAILY_ENERGY: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
        },
        source="user",
        entry_id="test-entry",
        discovery_keys={},
    )
    flow = CatchSolarConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    hass.config_entries.async_get_known_entry = Mock(return_value=entry)

    result = await flow.async_step_init(
        {
            CONF_SCAN_INTERVAL: 300,
            CONF_ENABLE_LIVE_DATA: True,
            CONF_ENABLE_DAILY_ENERGY: True,
            CONF_PRIMARY_LOAD_LABEL: "Pool Pump",
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 300,
        CONF_ENABLE_LIVE_DATA: True,
        CONF_ENABLE_DAILY_ENERGY: True,
        CONF_PRIMARY_LOAD_LABEL: "Pool Pump",
    }


async def test_options_flow_init_form_uses_existing_defaults(hass) -> None:
    entry = _config_entry(
        version=1,
        minor_version=1,
        domain="catchsolar",
        title="Home",
        data={},
        options={
            CONF_SCAN_INTERVAL: 900,
            CONF_ENABLE_LIVE_DATA: False,
            CONF_ENABLE_DAILY_ENERGY: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
        },
        source="user",
        entry_id="test-entry",
        discovery_keys={},
    )
    flow = CatchSolarConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    hass.config_entries.async_get_known_entry = Mock(return_value=entry)

    result = await flow.async_step_init()

    assert result["type"] is FlowResultType.FORM


async def test_reauth_rejects_credentials_for_another_account(hass) -> None:
    entry = SimpleNamespace(
        entry_id="test-entry",
        unique_id="42:1234",
        title="Home",
        data={
            CONF_USERNAME: "old@example.com",
            CONF_PASSWORD: "old-secret",
            CONF_ACCOUNT_ID: 42,
            CONF_LOCATION_ID: 1234,
        },
        options={},
    )
    flow = _attach_hass(CatchSolarConfigFlow(), hass)
    flow.context = {"entry_id": entry.entry_id}
    flow._get_reauth_entry = Mock(return_value=entry)

    with patch("custom_components.catchsolar.config_flow.CatchSolarApiClient") as client_cls:
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value={"id": 99})
        client.async_get_locations = AsyncMock(return_value=[{"id": 1234, "name": "Home"}])

        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_mismatch = Mock(side_effect=Exception("wrong account"))

        with pytest.raises(Exception, match="wrong account"):
            await flow.async_step_reauth_confirm(
                {CONF_USERNAME: "new@example.com", CONF_PASSWORD: "new-secret"}
            )

    flow.async_set_unique_id.assert_awaited_once_with("99:1234")


async def test_reauth_updates_credentials_only_after_location_validation(hass) -> None:
    entry = SimpleNamespace(
        entry_id="test-entry",
        unique_id="42:1234",
        title="Home",
        data={
            CONF_USERNAME: "old@example.com",
            CONF_PASSWORD: "old-secret",
            CONF_ACCOUNT_ID: 42,
            CONF_LOCATION_ID: 1234,
        },
        options={},
    )
    flow = _attach_hass(CatchSolarConfigFlow(), hass)
    flow.context = {"entry_id": entry.entry_id}
    flow._get_reauth_entry = Mock(return_value=entry)

    with patch("custom_components.catchsolar.config_flow.CatchSolarApiClient") as client_cls:
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value={"id": 42})
        client.async_get_locations = AsyncMock(return_value=[{"id": 1234, "name": "Home"}])

        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_mismatch = Mock()
        flow.async_update_reload_and_abort = Mock(return_value={"type": "abort"})

        result = await flow.async_step_reauth_confirm(
            {CONF_USERNAME: "new@example.com", CONF_PASSWORD: "new-secret"}
        )

    assert result == {"type": "abort"}
    flow.async_update_reload_and_abort.assert_called_once_with(
        entry,
        data_updates={
            CONF_USERNAME: "new@example.com",
            CONF_PASSWORD: "new-secret",
            CONF_ACCOUNT_ID: 42,
        },
    )


async def test_reconfigure_allows_same_account_location_change(hass) -> None:
    entry = SimpleNamespace(
        entry_id="test-entry",
        unique_id="42:1234",
        data={
            CONF_USERNAME: "old@example.com",
            CONF_PASSWORD: "old-secret",
            CONF_ACCOUNT_ID: 42,
            CONF_LOCATION_ID: 1234,
        },
        options={CONF_PRIMARY_DEVICE_ID: 9001, CONF_SCAN_INTERVAL: 900},
    )
    flow = _attach_hass(CatchSolarConfigFlow(), hass)
    flow._get_reconfigure_entry = Mock(return_value=entry)
    flow._account_id = 42
    flow._username = "new@example.com"
    flow._password = "new-secret"
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock()
    flow.async_update_reload_and_abort = Mock(return_value={"type": "abort"})

    result = await flow._async_update_reconfigured_entry({"id": 5678, "name": "Away"})

    assert result == {"type": "abort"}
    flow.async_set_unique_id.assert_awaited_once_with("42:5678")
    flow._abort_if_unique_id_configured.assert_called_once_with()
    flow.async_update_reload_and_abort.assert_called_once_with(
        entry,
        unique_id="42:5678",
        data_updates={
            CONF_USERNAME: "new@example.com",
            CONF_PASSWORD: "new-secret",
            CONF_ACCOUNT_ID: 42,
            CONF_LOCATION_ID: 5678,
            CONF_LOCATION_NAME: "Away",
        },
        options={CONF_SCAN_INTERVAL: 900},
        reason="reconfigure_successful",
    )


async def test_reconfigure_rejects_credentials_for_another_account(hass) -> None:
    entry = SimpleNamespace(
        entry_id="test-entry",
        unique_id="42:1234",
        data={CONF_ACCOUNT_ID: 42, CONF_LOCATION_ID: 1234},
        options={},
    )
    flow = _attach_hass(CatchSolarConfigFlow(), hass)
    flow._get_reconfigure_entry = Mock(return_value=entry)
    flow._account_id = 99

    result = await flow._async_update_reconfigured_entry({"id": 5678, "name": "Away"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_options_flow_normalizes_automatic_primary_relay(hass) -> None:
    entry = _config_entry(
        version=1,
        minor_version=1,
        domain="catchsolar",
        title="Home",
        data={},
        options={
            CONF_SCAN_INTERVAL: 900,
            CONF_ENABLE_LIVE_DATA: False,
            CONF_ENABLE_DAILY_ENERGY: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
        },
        source="user",
        entry_id="test-entry",
        discovery_keys={},
    )
    flow = CatchSolarConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    hass.config_entries.async_get_known_entry = Mock(return_value=entry)

    result = await flow.async_step_init(
        {
            CONF_SCAN_INTERVAL: 300,
            CONF_ENABLE_LIVE_DATA: False,
            CONF_ENABLE_DAILY_ENERGY: False,
            CONF_PRIMARY_LOAD_LABEL: "Water Heater",
            CONF_PRIMARY_DEVICE_ID: "",
        }
    )

    assert CONF_PRIMARY_DEVICE_ID not in result["data"]
