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
- `8ec5600` — Add PNG icons and bump to `0.1.5`
- `f1f0e4b` — Convert icons to RGB for max HA compatibility
- `4c7c284` — Update status docs with legacy cleanup and icon fix details

## Current repo version status

- `custom_components/catchsolar/manifest.json` is `0.1.5`
- GitHub latest release: `v0.1.5`
- HACS installed version: `v0.1.5`

## 2026-06-29 clean reinstall test — completed

Full uninstall and reinstall cycle verified:

1. Removed Catch Solar config entry → devices and entities cleaned up automatically
2. Removed Catch Solar HACS from HACS → `custom_components/catchsolar/` directory deleted
3. Restarted Home Assistant → confirmed zero catchsolar traces
4. Reinstalled from HACS → downloaded v0.1.5
5. Restarted Home Assistant
6. Added integration via config flow → new entry `01KW8ST0QW6T3119ZG3WTZPYJ0`
7. Verified:
   - Location device: `Catch Solar Location 8382` (assigned to "outside" area)
   - Relay device: `Primary Load Relay 9310` (assigned to "outside" area)
   - Runtime sensors all present and reporting 0.0h
   - System logs clean — zero catchsolar errors or warnings

## Legacy cleanup — completed

### Pre-HACS YAML entities (first pass)
- `automation.catch_solar_water_heater_notification` — deleted via API
- `binary_sensor.custom_catchsolar_loadstate` — template helper deleted
- `sensor.water_heater_runtime_active` — template helper deleted
- `sensor.catch_solar_loadstate_raw` — YAML `command_line` section removed from `configuration.yaml`, entity removed from registry

### Legacy water_heater runtime helpers (second pass)
All 6 old runtime calculation helpers removed (they depended on the now-deleted `binary_sensor.custom_catchsolar_loadstate`):

- `sensor.water_heater_runtime_total_raw` — integration (Riemann sum) helper deleted
- `sensor.water_heater_runtime_total` — template helper deleted
- `sensor.water_heater_runtime_today` — utility_meter helper deleted
- `sensor.water_heater_runtime_today_display` — template helper deleted
- `sensor.water_heater_runtime_7_day_change_raw` — statistics helper deleted
- `sensor.water_heater_runtime_7_day_change` — template helper deleted

### Dashboard fix
- Energy 1 dashboard "Water Heater Runtime" section rewired to new Catch Solar sensors:
  - `sensor.catch_solar_location_8382_primary_load_runtime_24h` (Runtime 24h)
  - `sensor.catch_solar_location_8382_primary_load_runtime_7d_rolling` (Runtime 7d Rolling)

## Icon fix — completed

- Added `icon.png` (256×256, RGB) and `logo.png` (512×512, RGB) to the integration package
- Published as GitHub Release `v0.1.5`
- Icon shows on GitHub but HA frontend may still need investigation (possible browser cache or HA caching issue)
- The `/api/custom_icons/icon/catchsolar` endpoint requires authentication (returns 404 without auth)

## Remaining

- Investigate why the integration icon doesn't render in HA Settings → Devices & Services (likely frontend caching)
- Optionally set `primary_load_label` to `"Water Heater"` via Configure → Options
- Manually remove unused `catchsolar_loadstate_command` from `secrets.yaml` if desired (harmless to leave)

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site.
- The current upstream `undefined` series equals `Solar + Export/Import`.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one.
- Conclusion: keep `loadState` as the reliable Catch Solar signal and treat Monocle power series as approximate diagnostic telemetry only.
