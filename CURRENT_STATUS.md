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
- `3b8eac3` — Add primary load label option and tests
- `1021b5f` — Fix HA 2026.6 config flow and entity collisions
- `03fa9b1` — Clarify Monocle power feed behavior
- `3e5fa1c` — Bump version to `0.1.2`

## Local unpublished work

- Built-in primary-load runtime tracking with persisted state and restart recovery
- Three location-level runtime sensors:
  - `Primary Load Runtime 24h`
  - `Primary Load Runtime 7d Rolling`
  - `Primary Load Runtime Total`
- Config-entry removal cleanup for the persisted runtime store
- Semantic location and relay device naming cleanup
- Bundled local icon and logo assets
- README uninstall and clean-reinstall guidance for non-technical users

## Current repo version status

- `custom_components/catchsolar/manifest.json` is now `0.1.3` locally
- `main` currently points at `3e5fa1c` until the local `0.1.3` work is committed and pushed
- HACS currently reports:
  - `installed_version=v0.1.2`
  - `available_version=v0.1.2`
- A real HACS reinstall test requires publishing the local `0.1.3` work first

## Home Assistant side context

- HACS had already installed the integration and later reported both installed and available version as `v0.1.2`.
- The live config entry id is `01KW82PMQTTVX8AWT07PW40X49`.
- The next validation step is: publish `0.1.3`, remove the existing Catch Solar config entry, reinstall from HACS, then verify the runtime sensors and naming cleanup live in Home Assistant.

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps. Example: `2026-06-29T08:25:00+10:00` maps to `1782685500000`.
- Home Assistant history showed the Catch Solar entities being re-polled every minute via `last_reported`, even when the upstream bucket had not changed.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site, so exposing the latest non-null fallback as the sensor state was misleading.
- The current upstream `undefined` series equals `Solar + Export/Import`.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one, so they are not directly usable as canonical live power telemetry.
- Solar Analytics remains the most likely upstream source behind the Monocle power data, but the authenticated live endpoint flow was not conclusively resolved.
- Conclusion: keep `loadState` as the reliable Catch Solar signal and treat Monocle power series as approximate diagnostic telemetry only.
