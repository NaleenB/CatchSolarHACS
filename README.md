# Catch Solar HACS

Home Assistant custom integration for Catch Solar / The Monocle.

This integration connects to the Monocle API via a Home Assistant config flow and exposes:

- a location-level primary load-state entity for stable automations and dashboards
- built-in primary-load runtime sensors managed by the integration itself:
  - `Primary Load Runtime 24h`
  - `Primary Load Runtime 7d Rolling`
  - `Primary Load Runtime Total`
- device `loadState` as both a binary sensor and a raw diagnostic sensor
- device online/connectivity state
- device metadata sensors
- latest raw 24-hour Monocle power-series values
- reauthentication support when Monocle credentials change
- bundled local icon and logo assets for the custom component package

No user credentials belong in this repository. Users enter their Catch Solar credentials in Home Assistant during setup; Home Assistant stores them in the config entry.

## Important warning

The Monocle power sensors in this integration expose raw upstream `data24` bucketed values only.

- They are not directly usable as real-time household consumption, solar generation, or import/export truth.
- Treat them as approximate diagnostic telemetry, not canonical live power sensors.
- Do not assume one-to-one equivalence with inverter entities, utility-meter logic, or higher-frequency Home Assistant template/custom sensors.
- `loadState` remains the reliable Catch Solar signal for stable automations such as water-heater state tracking.
- The built-in runtime sensors are derived from the primary device `loadState`, not from Monocle power telemetry.

## Current v1 scope

- binary sensor for device `loadState`
- binary sensor for primary device `loadState`
- runtime sensors for the primary load on the location device:
  - `Primary Load Runtime 24h` — local-calendar-day runtime since midnight
  - `Primary Load Runtime 7d Rolling` — true trailing 7-day runtime
  - `Primary Load Runtime Total` — cumulative runtime since integration tracking began
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
5. Add the integration from Settings -> Devices & Services

## Uninstall / clean reinstall

For a clean reinstall, remove the Home Assistant config entry before removing the HACS package:

1. Go to Settings -> Devices & Services -> Catch Solar and remove the integration.
2. This removes the Catch Solar entities and devices and deletes the integration-managed persisted primary-load runtime store.
3. Remove `Catch Solar HACS` from HACS.
4. Restart Home Assistant.
5. Reinstall from HACS and add the integration again.

Removing the HACS package alone is not the clean-reset step. The config-entry removal is what clears the entities and the persisted runtime history.

## Setup

The config flow:

1. prompt for Catch Solar username and password
2. authenticate against Monocle
3. fetch available locations
4. let the user select a location if multiple exist
5. create entities automatically

## Notes

- This repo intentionally contains no real Catch Solar usernames, passwords, tokens, or personal location metadata.
- Polling interval and 24-hour power data are configurable in the integration options.
- The runtime sensors use hours as their native unit and round to 2 decimal places.
- `Primary Load Runtime 24h` intentionally means local-calendar-day runtime since midnight, even though the entity name uses `24h`.
- Runtime state is persisted by the integration and survives restarts, including the case where the primary load stays on across a restart.
- Runtime history starts when this integration begins tracking; it is not reconstructed from Recorder/history.
- The Monocle `data24` feed is upstream 5-minute bucketed telemetry, not a live second-by-second inverter feed.
- A 60-second polling interval can still be useful: entity attributes include `last_polled_at` so Home Assistant shows successful refreshes even when the upstream 5-minute bucket has not changed yet.
- The integration options also let users rename the location-level primary load entities to a semantic label such as `Water Heater`.
- Device names are presented in a semantic hybrid form such as `Catch Solar Location 8382` and `Water Heater Relay 3649` so IDs remain visible for debugging without surfacing bare numeric names.
- If credentials expire or change, Home Assistant can prompt for reauthentication through the config entry.
- Diagnostics are intended to be shareable: sensitive values such as usernames, passwords, and tokens are redacted.
- The Monocle power sensors intentionally present the raw upstream series names and values conservatively. They should be treated as Monocle telemetry only, not assumed to be identical to higher-frequency Home Assistant inverter/template sensors.
- Current observed upstream behavior on 2026-06-29:
  - `data24` advances in 5-minute buckets
  - `Total Consumption` can be `null` in the latest bucket
  - the current `undefined` series equals `Solar + Export/Import`
  - the power series do not align tightly enough with live HA sensors to be used as canonical power truth
- Version status observed on 2026-06-29:
  - repo manifest version: `0.1.4`
  - published releases observed during the investigation included `v0.1.2`
  - Home Assistant Integrations detail may lag until the browser is refreshed or Home Assistant reloads the updated integration code
