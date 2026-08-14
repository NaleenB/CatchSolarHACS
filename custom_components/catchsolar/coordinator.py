from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CatchSolarApiAuthError, CatchSolarApiClient, CatchSolarApiError
from .const import (
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)
from .parsing import normalize_device_entry, pick_primary_device
from .runtime import PrimaryLoadRuntimeTracker

_LOGGER = logging.getLogger(__name__)


class CatchSolarDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: CatchSolarApiClient,
        config: dict[str, Any],
        runtime_tracker: PrimaryLoadRuntimeTracker,
    ) -> None:
        scan_interval = int(config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="Catch Solar",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.config = config
        self.runtime_tracker = runtime_tracker

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            location_id = int(self.config[CONF_LOCATION_ID])
            location_name = self.config.get(CONF_LOCATION_NAME)
            # The selected location is stored in the config entry. Do not make the
            # primary-load state depend on a second, non-essential API request.
            location = {"id": location_id, "name": location_name}

            devices = [
                normalize_device_entry(item)
                for item in await self.api.async_get_devices(location_id)
            ]

            primary_device = pick_primary_device(devices) or {}
            primary_load_state = primary_device.get("load_state")
            processed_at = dt_util.utcnow()
            if primary_load_state is None:
                runtime_snapshot = self.runtime_tracker.get_snapshot(processed_at)
            else:
                runtime_snapshot = await self.runtime_tracker.async_process(
                    int(primary_load_state) == 1,
                    processed_at,
                )

            return {
                "location": location,
                "devices": devices,
                "primary_device_id": primary_device.get("id"),
                "runtime": runtime_snapshot.as_dict(),
                "last_polled_at": processed_at.isoformat(),
            }
        except CatchSolarApiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CatchSolarApiError as err:
            raise UpdateFailed(str(err)) from err
