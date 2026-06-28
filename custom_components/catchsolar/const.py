from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "catchsolar"
API_BASE = "https://monocle0.edde.world"

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

CONF_ACCOUNT_ID = "account_id"
CONF_LOCATION_ID = "location_id"
CONF_LOCATION_NAME = "location_name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_POWER_DATA = "enable_power_data"

DEFAULT_SCAN_INTERVAL_SECONDS = 600
DEFAULT_ENABLE_POWER_DATA = True
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)

POWER_SERIES_MAP = {
    "Solar": "solar_power",
    "Total Consumption": "total_consumption_power",
    "Export/Import": "export_import_power",
}
