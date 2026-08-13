from __future__ import annotations

from typing import Any

POWER_SERIES_MAP = {
    "Solar": "solar_power",
    "Total Consumption": "total_consumption_power",
    "Export/Import": "export_import_power",
}

DAILY_ENERGY_SERIES_MAP = {
    "Solar": "solar_yield_energy",
    "Export": "grid_export_energy",
    "Import": "grid_import_energy",
    "Total Consumption": "house_consumption_energy",
    "Consumed Solar": "consumed_solar_energy",
}

LIVE_SITE_POWER_MAP = {
    "mainsPWR": "mains_power",
    "solarPWR": "solar_power",
    "housePWR": "house_power",
    "batteryPWR": "battery_power",
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


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_daily_energy(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return {"series": {}, "raw_total_wh": {}, "x_axis": []}

    energy: dict[str, float] = {}
    raw_total_wh: dict[str, float] = {}
    for item in result.get("seriesList", []):
        if not isinstance(item, dict):
            continue
        key = DAILY_ENERGY_SERIES_MAP.get(item.get("name"))
        total_wh = _number(item.get("totalWh"))
        if key is None or total_wh is None:
            continue
        raw_total_wh[key] = total_wh
        energy[key] = round(abs(total_wh) / 1000, 3)

    x_axis = result.get("xAxis")
    return {
        "series": energy,
        "raw_total_wh": raw_total_wh,
        "x_axis": list(x_axis) if isinstance(x_axis, list) else [],
    }


def extract_live_event(payload: dict[str, Any]) -> dict[str, Any]:
    site_power = {
        target: _number(payload.get(source)) for source, target in LIVE_SITE_POWER_MAP.items()
    }

    csip = payload.get("csip")
    if not isinstance(csip, dict):
        csip = {}
    active_control = _number(csip.get("activeControlW"))
    limits = {
        "import_limit": _number(csip.get("activeImportW")),
        "export_limit": abs(active_control) if active_control is not None else None,
    }

    actors: list[dict[str, Any]] = []
    controllable = payload.get("controllable")
    if isinstance(controllable, dict):
        for actor_class, entries in controllable.items():
            if not isinstance(entries, list):
                continue
            for item in entries:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                actors.append(
                    {
                        "id": str(item["id"]),
                        "class": str(actor_class),
                        "key": item.get("key"),
                        "name": item.get("name") or item.get("key") or str(actor_class),
                        "power": _number(item.get("pwr")),
                        "state": item.get("state"),
                        "soc": _number(item.get("soc")),
                    }
                )

    channels: list[dict[str, Any]] = []
    raw_channels = payload.get("channels")
    if isinstance(raw_channels, list):
        for item in raw_channels:
            if not isinstance(item, dict):
                continue
            name = str(item.get("channelName") or "").strip()
            channel_type = str(item.get("channelType") or "").strip()
            if not name and not channel_type:
                continue
            channels.append(
                {
                    "key": f"{channel_type}:{name}",
                    "name": name or channel_type,
                    "type": channel_type,
                    "power": _number(item.get("channelPWR")),
                }
            )

    return {
        "site_power": site_power,
        "limits": limits,
        "actors": actors,
        "channels": channels,
        "device_count": payload.get("deviceCount"),
    }
