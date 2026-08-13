from datetime import timedelta
from typing import TypedDict

from homeassistant.const import Platform

DOMAIN = "catchsolar"
API_BASE = "https://monocle0.edde.world"

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCOUNT_ID = "account_id"
CONF_LOCATION_ID = "location_id"
CONF_LOCATION_NAME = "location_name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_POWER_DATA = "enable_power_data"
CONF_ENABLE_LIVE_DATA = "enable_live_data"
CONF_ENABLE_DAILY_ENERGY = "enable_daily_energy"
CONF_PRIMARY_LOAD_LABEL = "primary_load_label"

DEFAULT_SCAN_INTERVAL_SECONDS = 600
DEFAULT_ENABLE_POWER_DATA = True
DEFAULT_ENABLE_LIVE_DATA = True
DEFAULT_ENABLE_DAILY_ENERGY = True
DEFAULT_PRIMARY_LOAD_LABEL = "Primary Load"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)


# Keep experimental additions identifiable in diagnostics and documentation so
# they can be disabled or removed independently from the original integration.
class ExperimentalFeature(TypedDict):
    option: str
    default: bool
    runtime_key: str
    introduced_in: str


EXPERIMENTAL_FEATURES: dict[str, ExperimentalFeature] = {
    "live_socketio_telemetry": {
        "option": CONF_ENABLE_LIVE_DATA,
        "default": DEFAULT_ENABLE_LIVE_DATA,
        "runtime_key": "live_coordinator",
        "introduced_in": "0.2.0",
    },
    "daily_energy_meters": {
        "option": CONF_ENABLE_DAILY_ENERGY,
        "default": DEFAULT_ENABLE_DAILY_ENERGY,
        "runtime_key": "daily_energy_coordinator",
        "introduced_in": "0.2.0",
    },
}

DAILY_ENERGY_UPDATE_INTERVAL_SECONDS = 60
LIVE_EVENT_STALE_SECONDS = 30

RUNTIME_SENSOR_24H = "runtime_24h"
RUNTIME_SENSOR_7D_ROLLING = "runtime_7d_rolling"
RUNTIME_SENSOR_TOTAL = "runtime_total"

POWER_SERIES_MAP = {
    "Solar": "solar_power",
    "Total Consumption": "total_consumption_power",
    "Export/Import": "export_import_power",
}
