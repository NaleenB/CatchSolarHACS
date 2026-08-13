from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import socketio
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CatchSolarApiAuthError, CatchSolarApiClient, CatchSolarApiError
from .const import (
    API_BASE,
    DAILY_ENERGY_UPDATE_INTERVAL_SECONDS,
    LIVE_EVENT_STALE_SECONDS,
    LIVE_PUBLISH_INTERVAL_SECONDS,
)
from .parsing import extract_daily_energy, extract_live_event

_LOGGER = logging.getLogger(__name__)


class CatchSolarDailyEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: CatchSolarApiClient,
        config: dict[str, Any],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Catch Solar daily energy",
            update_interval=timedelta(seconds=DAILY_ENERGY_UPDATE_INTERVAL_SECONDS),
        )
        self.api = api
        self.config = config
        self.data: dict[str, Any] = {
            "location": {
                "id": int(config["location_id"]),
                "name": config.get("location_name"),
            },
            "series": {},
            "raw_total_wh": {},
            "x_axis": [],
            "window_start": None,
            "window_end": None,
            "last_polled_at": None,
        }
        self.last_update_success = False

    async def _async_update_data(self) -> dict[str, Any]:
        location_id = int(self.config["location_id"])
        local_now = dt_util.now()
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_end = local_start + timedelta(days=1)
        date_from = _iso_z(dt_util.as_utc(local_start))
        date_to = _iso_z(dt_util.as_utc(local_end))

        try:
            parsed = extract_daily_energy(
                await self.api.async_get_daily_energy(location_id, date_from, date_to)
            )
        except CatchSolarApiAuthError as err:
            raise UpdateFailed(str(err)) from err
        except CatchSolarApiError as err:
            raise UpdateFailed(str(err)) from err

        if not parsed["series"]:
            raise UpdateFailed("Daily energy response did not contain supported series")

        parsed.update(
            {
                "location": {
                    "id": location_id,
                    "name": self.config.get("location_name"),
                },
                "window_start": date_from,
                "window_end": date_to,
                "last_polled_at": dt_util.utcnow().isoformat(),
            }
        )
        return parsed


class CatchSolarLiveCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
    ) -> None:
        super().__init__(hass, _LOGGER, name="Catch Solar live telemetry")
        self.config = config
        self._location = {
            "id": int(config["location_id"]),
            "name": config.get("location_name"),
        }
        self.data: dict[str, Any] = {
            "location": dict(self._location),
            "site_power": {},
            "limits": {},
            "actors": [],
            "channels": [],
            "device_count": None,
            "last_event_at": None,
            "last_published_at": None,
        }
        self.last_update_success = False
        self._stale_handle: asyncio.TimerHandle | None = None
        self._publish_handle: asyncio.TimerHandle | None = None
        self._pending_data: dict[str, Any] | None = None
        self._last_publish_time: float | None = None

    async def async_handle_event(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            _LOGGER.debug("Ignoring non-object Catch Solar live event")
            return

        parsed = extract_live_event(payload)
        parsed["location"] = dict(self._location)
        parsed["last_event_at"] = dt_util.utcnow().isoformat()
        self._schedule_stale_check()
        self._queue_for_publication(parsed)

    async def async_handle_disconnect(self) -> None:
        self._cancel_stale_check()
        self._cancel_publication()
        self.async_set_update_error(UpdateFailed("Catch Solar live connection is offline"))

    async def async_shutdown(self) -> None:
        self._cancel_stale_check()
        self._cancel_publication()
        await super().async_shutdown()

    async def async_stop_live(self) -> None:
        self._cancel_stale_check()
        self._cancel_publication()
        self.async_set_update_error(UpdateFailed("Catch Solar live connection stopped"))

    def _queue_for_publication(self, data: dict[str, Any]) -> None:
        """Publish the newest live snapshot no more than once every five seconds."""
        now = self.hass.loop.time()
        if self._last_publish_time is None or not self.last_update_success:
            self._publish(data, now)
            return

        elapsed = now - self._last_publish_time
        if elapsed >= LIVE_PUBLISH_INTERVAL_SECONDS:
            self._publish(data, now)
            return

        self._pending_data = data
        if self._publish_handle is None:
            self._publish_handle = self.hass.loop.call_later(
                LIVE_PUBLISH_INTERVAL_SECONDS - elapsed,
                self._publish_pending,
            )

    def _publish_pending(self) -> None:
        self._publish_handle = None
        if self._pending_data is not None:
            self._publish(self._pending_data, self.hass.loop.time())

    def _publish(self, data: dict[str, Any], published_at: float) -> None:
        self._cancel_publish_handle()
        self._pending_data = None
        self._last_publish_time = published_at
        data["last_published_at"] = dt_util.utcnow().isoformat()
        self.async_set_updated_data(data)

    def _cancel_publish_handle(self) -> None:
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def _cancel_publication(self) -> None:
        self._cancel_publish_handle()
        self._pending_data = None

    def _schedule_stale_check(self) -> None:
        self._cancel_stale_check()
        self._stale_handle = self.hass.loop.call_later(
            LIVE_EVENT_STALE_SECONDS,
            self._mark_stale,
        )

    def _cancel_stale_check(self) -> None:
        if self._stale_handle is not None:
            self._stale_handle.cancel()
            self._stale_handle = None

    def _mark_stale(self) -> None:
        self._stale_handle = None
        self._cancel_publication()
        self.async_set_update_error(
            UpdateFailed(
                f"No Catch Solar live event received for {LIVE_EVENT_STALE_SECONDS} seconds"
            )
        )


class CatchSolarLiveClient:
    def __init__(
        self,
        api: CatchSolarApiClient,
        session: ClientSession,
        location_id: int,
        coordinator: CatchSolarLiveCoordinator,
    ) -> None:
        self._api = api
        self._session = session
        self._location_id = location_id
        self._coordinator = coordinator
        self._task: asyncio.Task[None] | None = None
        self._sio: socketio.AsyncClient | None = None
        self._stopping = False

    async def async_start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(
            self._async_connection_loop(),
            name=f"catchsolar-live-{self._location_id}",
        )

    async def async_stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
        await self._async_disconnect()
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._coordinator.async_stop_live()

    async def _async_connection_loop(self) -> None:
        backoff = 5
        refresh_token = False
        while not self._stopping:
            try:
                token = await self._api.async_get_access_token(refresh=refresh_token)
                refresh_token = True
                sio = socketio.AsyncClient(
                    reconnection=False,
                    logger=False,
                    engineio_logger=False,
                    http_session=self._session,
                )
                self._sio = sio

                @sio.on("event")
                async def _handle_event(payload: Any) -> None:
                    await self._coordinator.async_handle_event(payload)

                @sio.event
                async def disconnect(reason: Any = None) -> None:
                    if not self._stopping:
                        await self._coordinator.async_handle_disconnect()

                await sio.connect(
                    API_BASE,
                    auth={"token": token, "locationId": self._location_id},
                    transports=["websocket"],
                    socketio_path="socket.io",
                    wait_timeout=20,
                )
                backoff = 5
                await sio.wait()
            except asyncio.CancelledError:
                raise
            except CatchSolarApiAuthError:
                await self._coordinator.async_handle_disconnect()
                _LOGGER.warning("Unable to authenticate the optional Catch Solar live feed")
            except Exception as err:
                await self._coordinator.async_handle_disconnect()
                _LOGGER.debug("Catch Solar live connection failed: %s", err)
            finally:
                await self._async_disconnect()

            if not self._stopping:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _async_disconnect(self) -> None:
        sio = self._sio
        self._sio = None
        if sio is None:
            return
        try:
            async with asyncio.timeout(5):
                await sio.disconnect()
        except TimeoutError:
            _LOGGER.debug("Timed out while closing Catch Solar live connection")
        except Exception:
            _LOGGER.debug("Error while closing Catch Solar live connection", exc_info=True)


def _iso_z(value) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
