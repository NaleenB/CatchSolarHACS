# Catch Solar HACS

Home Assistant custom integration for Catch Solar / The Monocle.

This integration connects to the Monocle API via a Home Assistant config flow and exposes:

- a location-level primary load-state entity for stable automations/dashboards
- device `loadState` as both a binary sensor and a raw diagnostic sensor
- device online/connectivity state
- device metadata sensors
- latest raw 24-hour Monocle power-series values
- reauthentication support when Monocle credentials change

No user credentials belong in this repository. Users enter their Catch Solar credentials in Home Assistant during setup; Home Assistant stores them in the config entry.

## Current v1 scope

- binary sensor for device `loadState`
- binary sensor for primary device `loadState`
- raw sensor for primary device `loadState`
- raw sensor for device `loadState`
- binary sensor for device online status
- diagnostic sensors for serial, device type, channel types, and control flags
- sensors for the latest Monocle `data24` bucket:
  - Monocle Solar Power
  - Monocle Total Consumption Power
  - Monocle Export/Import Power

## Installation

Private bootstrap phase:

1. In HACS, add this repo as a custom repository.
2. Category: `Integration`
3. Install `Catch Solar HACS`
4. Restart Home Assistant
5. Add the integration from Settings → Devices & Services

## Setup

The config flow:

1. prompt for Catch Solar username/password
2. authenticate against Monocle
3. fetch available locations
4. let the user select a location if multiple exist
5. create entities automatically

## Notes

- This repo intentionally contains no real Catch Solar usernames, passwords, tokens, or personal location metadata.
- Polling interval and 24-hour power data are configurable in the integration options.
- The Monocle `data24` feed is upstream 5-minute bucketed telemetry, not a live second-by-second inverter feed.
- A 60-second polling interval can still be useful: entity attributes include `last_polled_at` so Home Assistant shows successful refreshes even when the upstream 5-minute bucket has not changed yet.
- The integration options also let users rename the location-level primary load entities to a semantic label such as `Water Heater`.
- If credentials expire or change, Home Assistant can prompt for reauthentication through the config entry.
- Diagnostics are intended to be shareable: sensitive values such as usernames, passwords, and tokens are redacted.
- The Monocle power sensors intentionally present the raw upstream series names and values conservatively. They should be treated as Monocle telemetry, not assumed to be identical to higher-frequency Home Assistant inverter/template sensors.
- Water-heater runtime helpers/automations are better handled in Home Assistant, not hard-coded into the integration.
