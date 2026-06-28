from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from json import JSONDecodeError

from .const import API_BASE
from .parsing import parse_locations


class CatchSolarApiError(Exception):
    """Base API error."""


class CatchSolarApiAuthError(CatchSolarApiError):
    """Authentication failed."""


class CatchSolarApiClient:
    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        authenticated: bool = False,
        retry_auth: bool = True,
    ) -> dict[str, Any] | list[Any]:
        if authenticated and self._token is None:
            await self.async_login()

        headers = {"Content-Type": "application/json"}
        if authenticated and self._token is not None:
            headers["Authorization"] = f"Token {self._token}"

        try:
            async with self._session.request(
                method,
                f"{API_BASE}{path}",
                json=json_payload,
                headers=headers,
                timeout=30,
            ) as response:
                if response.status == 401:
                    if retry_auth:
                        self._token = None
                        await self.async_login()
                        return await self._request_json(
                            method,
                            path,
                            json_payload=json_payload,
                            authenticated=authenticated,
                            retry_auth=False,
                        )
                    raise CatchSolarApiAuthError("Authentication failed")

                response.raise_for_status()
                return await response.json()
        except CatchSolarApiAuthError:
            raise
        except ClientResponseError as err:
            raise CatchSolarApiError(f"HTTP error {err.status} for {path}") from err
        except (ClientError, asyncio.TimeoutError, JSONDecodeError) as err:
            raise CatchSolarApiError(f"Request failed for {path}") from err

    async def async_login(self) -> dict[str, Any]:
        payload = await self._request_json(
            "POST",
            "/auth/login",
            json_payload={"username": self._username, "password": self._password},
            authenticated=False,
            retry_auth=False,
        )
        if not isinstance(payload, dict) or "accessToken" not in payload:
            raise CatchSolarApiAuthError("Missing access token")
        self._token = str(payload["accessToken"])
        return payload

    async def async_get_locations(self) -> list[dict[str, Any]]:
        payload = await self._request_json(
            "POST",
            "/data/locations",
            json_payload={},
            authenticated=True,
        )
        if not isinstance(payload, dict):
            raise CatchSolarApiError("Invalid locations payload")
        return parse_locations(payload)

    async def async_get_devices(self, location_id: int) -> list[dict[str, Any]]:
        payload = await self._request_json(
            "POST",
            "/data/devices",
            json_payload={"locationId": location_id},
            authenticated=True,
        )
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, list):
                payload = result
        if not isinstance(payload, list):
            raise CatchSolarApiError("Invalid devices payload")
        return [item for item in payload if isinstance(item, dict)]

    async def async_get_data24(self, location_id: int, date_to: str) -> dict[str, Any]:
        payload = await self._request_json(
            "POST",
            "/data/data24",
            json_payload={"locationId": location_id, "dateTo": date_to},
            authenticated=True,
        )
        if not isinstance(payload, dict):
            raise CatchSolarApiError("Invalid data24 payload")
        return payload
