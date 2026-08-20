from __future__ import annotations

from typing import Any

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
    return [
        item
        for item in result
        if isinstance(item, dict) and _positive_int(item.get("id")) is not None
    ]


def normalize_device_entry(entry: dict[str, Any]) -> dict[str, Any]:
    device = entry.get("device")
    if not isinstance(device, dict):
        device = {}

    return {
        "id": _positive_int(device.get("id")),
        "device_name": device.get("deviceName"),
        "serial_number": device.get("serialNumber"),
        "device_type": device.get("deviceType"),
        "location_id": _positive_int(device.get("locationId")),
        "channel_1_type": device.get("ch1Type"),
        "channel_2_type": device.get("ch2Type"),
        "controlling_load": device.get("controllingLoad"),
        "controlling_inverter": device.get("controllingInverter"),
        "impl_class": device.get("implClass"),
        "load_state": _binary_value(entry.get("loadState")),
        "online": _binary_value(entry.get("online")),
    }


def pick_primary_device(
    devices: list[dict[str, Any]], preferred_device_id: int | None = None
) -> dict[str, Any] | None:
    """Select the configured relay, or a deterministic automatic candidate."""
    candidates = [
        device for device in devices if _binary_value(device.get("controlling_load")) == 1
    ]
    if preferred_device_id is not None:
        return next(
            (device for device in candidates if device.get("id") == preferred_device_id),
            None,
        )
    return min(
        candidates,
        key=lambda device: int(device["id"]) if isinstance(device.get("id"), int) else 0,
        default=None,
    )


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _binary_value(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed in (0, 1) else None


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
    for key in ("solar_power", "house_power"):
        if site_power[key] is not None:
            site_power[key] = abs(site_power[key])

    csip = payload.get("csip")
    if not isinstance(csip, dict):
        csip = {}
    active_control = _number(csip.get("activeControlW"))
    limits = {
        "import_limit": _number(csip.get("activeImportW")),
        "active_control": active_control,
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

    # Catch's channel payload has no stable upstream ID. Type and name are the
    # only usable entity identity; if the upstream repeats that identity, keep
    # the last value rather than creating unstable duplicate entities.
    channels_by_key: dict[str, dict[str, Any]] = {}
    raw_channels = payload.get("channels")
    if isinstance(raw_channels, list):
        for item in raw_channels:
            if not isinstance(item, dict):
                continue
            name = str(item.get("channelName") or "").strip()
            channel_type = str(item.get("channelType") or "").strip()
            if name.casefold() == "undefined" or channel_type.casefold() == "undefined":
                continue
            if not name and not channel_type:
                continue
            key = f"{channel_type}:{name}"
            channels_by_key[key] = {
                "key": key,
                "name": name or channel_type,
                "type": channel_type,
                "power": _number(item.get("channelPWR")),
            }

    return {
        "site_power": site_power,
        "limits": limits,
        "actors": actors,
        "channels": list(channels_by_key.values()),
        "device_count": payload.get("deviceCount"),
    }
