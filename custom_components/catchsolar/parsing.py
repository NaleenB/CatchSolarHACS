from __future__ import annotations

from typing import Any

POWER_SERIES_MAP = {
    "Solar": "solar_power",
    "Total Consumption": "total_consumption_power",
    "Export/Import": "export_import_power",
}


def parse_locations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result")
    if not isinstance(result, list):
        return []
    return [item for item in result if isinstance(item, dict)]


def normalize_device_entry(entry: dict[str, Any]) -> dict[str, Any]:
    device = entry.get("device")
    if not isinstance(device, dict):
        device = {}

    return {
        "id": device.get("id"),
        "device_name": device.get("deviceName"),
        "serial_number": device.get("serialNumber"),
        "device_type": device.get("deviceType"),
        "location_id": device.get("locationId"),
        "channel_1_type": device.get("ch1Type"),
        "channel_2_type": device.get("ch2Type"),
        "controlling_load": device.get("controllingLoad"),
        "controlling_inverter": device.get("controllingInverter"),
        "impl_class": device.get("implClass"),
        "load_state": entry.get("loadState"),
        "online": entry.get("online"),
    }


def pick_primary_device(devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    for device in devices:
        if int(device.get("controlling_load", 0) or 0) == 1:
            return device
    return devices[0] if devices else None


def _latest_non_null(values: list[Any]) -> float | int | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def extract_latest_power_series(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return {"timestamp_ms": None, "series": {}, "latest_non_null_series": {}}

    x_axis = result.get("xAxis")
    timestamp_ms = x_axis[-1] if isinstance(x_axis, list) and x_axis else None

    extracted: dict[str, Any] = {}
    latest_non_null_series: dict[str, Any] = {}
    for series in result.get("seriesList", []):
        if not isinstance(series, dict):
            continue
        name = series.get("name")
        key = POWER_SERIES_MAP.get(name)
        data = series.get("data")
        if key is None or not isinstance(data, list):
            continue
        extracted[key] = data[-1] if data else None
        latest_non_null_series[key] = _latest_non_null(data)

    return {
        "timestamp_ms": timestamp_ms,
        "series": extracted,
        "latest_non_null_series": latest_non_null_series,
    }
