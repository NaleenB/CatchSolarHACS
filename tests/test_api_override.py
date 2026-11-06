from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.catchsolar.api import CatchSolarApiClient, CatchSolarApiError


@pytest.fixture
def client() -> CatchSolarApiClient:
    return CatchSolarApiClient(object(), "user@example.com", "secret")


async def test_get_actors_returns_string_entries(client) -> None:
    client._request_json = AsyncMock(
        return_value={"success": True, "result": ["SR.3649", 9310, "GLD.SR.3649"]}
    )

    actors = await client.async_get_actors(8382)

    assert actors == ["SR.3649", "GLD.SR.3649"]
    client._request_json.assert_awaited_once_with(
        "POST",
        "/fleet/get-location-actors",
        json_payload={"locationId": 8382},
        authenticated=True,
    )


async def test_save_override_posts_mode_and_duration(client) -> None:
    client._request_json = AsyncMock(return_value={"success": True, "result": "OK"})

    await client.async_save_override(8382, "GLD.SR.3649", "on", 90)

    client._request_json.assert_awaited_once_with(
        "POST",
        "/data/saveOverride",
        json_payload={
            "actorID": "GLD.SR.3649",
            "locationId": 8382,
            "override": {"validUntil": 90, "mode": "on"},
        },
        authenticated=True,
    )


async def test_remove_override_posts_actor(client) -> None:
    client._request_json = AsyncMock(return_value={"success": True, "result": "OK"})

    await client.async_remove_override(8382, "GLD.SR.3649")

    client._request_json.assert_awaited_once_with(
        "POST",
        "/data/removeOverride",
        json_payload={"actorID": "GLD.SR.3649", "locationId": 8382},
        authenticated=True,
    )


async def test_save_override_surfaces_upstream_message(client) -> None:
    client._request_json = AsyncMock(
        return_value={
            "success": False,
            "result": {"message": "field mode does not exist in screen"},
        }
    )

    with pytest.raises(CatchSolarApiError, match="field mode does not exist"):
        await client.async_save_override(8382, "GLD.SR.3649", "on", 90)


async def test_get_override_state_reads_screen_definition(client) -> None:
    client._request_json = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "fields": [
                    {"id": "validUntil", "currentValue": 1793944841483},
                    {"id": "mode", "currentValue": "on"},
                ]
            },
        }
    )

    state = await client.async_get_override_state(8382, "GLD.SR.3649")

    assert state["mode"] == "on"
    assert state["expires_at"] is not None
    client._request_json.assert_awaited_once_with(
        "POST",
        "/data/getScreenDef",
        json_payload={"actorID": "GLD.SR.3649", "locationId": 8382},
        authenticated=True,
    )
