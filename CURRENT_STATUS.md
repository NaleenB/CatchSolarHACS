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

## Current repo version status

- `custom_components/catchsolar/manifest.json` is `0.1.5`
- GitHub latest release: `v0.1.5`
- HACS installed version: `v0.1.5`

## 2026-06-29 clean reinstall — completed

- Removed old config entry `01KW82PMQTTVX8AWT07PW40X49`
- Re-added via config flow → new entry `01KW8QFZPNKEFZMZ8BNGSPYPKS`
- Location device: `Catch Solar Location 8382`
- Relay device: `Primary Load Relay 9310` (default label; change `primary_load_label` to `"Water Heater"` via Configure → Options)
- Runtime sensors created and working
- System logs clean after restart

## Legacy cleanup — completed

Removed the old YAML-based entities:

- `automation.catch_solar_water_heater_notification` — deleted via API
- `binary_sensor.custom_catchsolar_loadstate` — template helper deleted
- `sensor.water_heater_runtime_active` — template helper deleted
- `sensor.catch_solar_loadstate_raw` — YAML `command_line` section removed from `configuration.yaml`, entity removed from registry
- `catchsolar_loadstate_command` secret in `secrets.yaml` is now unused (harmless, can be removed manually)

## Icon fix — completed

- Added `icon.png` (256×256, RGB) and `logo.png` (512×512, RGB) to the integration package
- Published as GitHub Release `v0.1.5`
- Deployed via HACS update + HA restart
- The integration tile in Settings → Devices & Services should now show the Catch Solar icon
- If the icon is still blank after restart, do a hard browser refresh (Cmd+Shift+R in Safari)

## Remaining

- Optionally set `primary_load_label` to `"Water Heater"` via Configure → Options
- Manually remove unused `catchsolar_loadstate_command` from `secrets.yaml` if desired (harmless to leave)

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site.
- The current upstream `undefined` series equals `Solar + Export/Import`.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one.
- Conclusion: keep `loadState` as the reliable Catch Solar signal and treat Monocle power series as approximate diagnostic telemetry only.
