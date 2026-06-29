# CatchSolarHACS current status

Last updated: 2026-06-29

## Repo

- Local path: `/Users/naleen/coding_projects/CatchSolarHACS`
- GitHub: `NaleenB/CatchSolarHACS`
- Visibility: public

## Recent pushed work

- `274d052` — Initial Catch Solar HACS scaffold
- `6735b57` — Refine Catch Solar integration scaffold
- `dcd47a4` — Add reauth and diagnostics support
- `3b8e3ac` — Add primary load label option and tests
- `1021b5f` — Fix HA 2026.6 config flow and entity collisions
- `03fa9b1` — Clarify Monocle power feed behavior
- `3e5fa1c` — Bump version to `0.1.2`
- `64ec1de` — Add runtime sensors and branding (published as `0.1.3`)
- `b470a5e` — Fix location primary load label entities (published as `0.1.4`)

## Local unpublished work

- Added `icon.png` (256×256) and `logo.png` (512×512) for the integration tile icon and brand logo
- Bumped manifest version to `0.1.5`

## Current repo version status

- `custom_components/catchsolar/manifest.json` is now `0.1.5` locally
- `main` currently includes the PNG icon/logo assets and version bump

## 2026-06-29 clean reinstall — completed

- Removed old config entry `01KW82PMQTTVX8AWT07PW40X49`
- Re-added via config flow → new entry `01KW8QFZPNKEFZMZ8BNGSPYPKS`
- Location device: `Catch Solar Location 8382`
- Relay device: `Primary Load Relay 9310` (default label; change `primary_load_label` to `"Water Heater"` if desired)
- Runtime sensors created:
  - `sensor.catch_solar_location_8382_primary_load_runtime_24h`
  - `sensor.catch_solar_location_8382_primary_load_runtime_7d_rolling`
  - `sensor.catch_solar_location_8382_primary_load_runtime_total`
- System logs clean after restart

## Legacy cleanup — completed

Removed the old YAML-based entities that predated the HACS integration:

- `automation.catch_solar_water_heater_notification` — deleted via API
- `binary_sensor.custom_catchsolar_loadstate` — template helper deleted (entry `01KW71D8BATHHY0R0PB2M79KV0`)
- `sensor.water_heater_runtime_active` — template helper deleted (entry `01KW71D8QRB3MVAHWQZN9D1X4D`)
- `sensor.catch_solar_loadstate_raw` — YAML `command_line` section removed from `configuration.yaml`, entity removed from registry
- `catchsolar_loadstate_command` secret in `secrets.yaml` is now unused (harmless, can be removed manually)

## Remaining to-do

- Push `0.1.5` with PNG icons to GitHub, tag the release, update via HACS to fix the empty integration icon
- Optionally set `primary_load_label` to `"Water Heater"` via Configure → Options

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps. Example: `2026-06-29T08:25:00+10:00` maps to `1782685500000`.
- Home Assistant history showed the Catch Solar entities being re-polled every minute via `last_reported`, even when the upstream bucket had not changed.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site, so exposing the latest non-null fallback as the sensor state was misleading.
- The current upstream `undefined` series equals `Solar + Export/Import`.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one, so they are not directly usable as canonical live power telemetry.
- Solar Analytics remains the most likely upstream source behind the Monocle power data, but the authenticated live endpoint flow was not conclusively resolved.
- Conclusion: keep `loadState` as the reliable Catch Solar signal and treat Monocle power series as approximate diagnostic telemetry only.
