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

## Current local-only work (not yet committed)

Home Assistant 2026.6 compatibility fix plus Monocle feed cleanup:

- renamed the custom `device_entry` entity property to avoid colliding with HA core
- renamed the custom options-flow `config_entry` attribute to avoid colliding with HA core
- bumped integration version to `0.1.1`
- clarified power sensor names to explicitly reflect raw Monocle telemetry
- stopped backfilling stale power values when the latest Monocle bucket is `null`
- added `last_polled_at` plus bucket timestamp metadata so 60-second polling is visible even when Monocle only publishes a new 5-minute bucket
- added regression tests covering both the HA compatibility fix and the power-series parsing/entity metadata behavior

Modified files:

- `CURRENT_STATUS.md`
- `README.md`
- `custom_components/catchsolar/binary_sensor.py`
- `custom_components/catchsolar/config_flow.py`
- `custom_components/catchsolar/entity.py`
- `custom_components/catchsolar/manifest.json`
- `custom_components/catchsolar/coordinator.py`
- `custom_components/catchsolar/parsing.py`
- `custom_components/catchsolar/sensor.py`
- `tests/test_config_flow.py`
- `tests/test_parsing.py`
- `tests/test_entity.py`

Validation already run:

- `PYTHONPYCACHEPREFIX=/private/tmp/catchsolar-pyc python3 -m py_compile custom_components/catchsolar/*.py tests/*.py` passed
- `pytest` passed: `9 passed, 3 skipped`

## Status of paused work

User asked to continue the full rollout:

1. commit the HA 2026.6 compatibility fix
2. push a patch release
3. update HACS in live Home Assistant
4. verify the options flow with a semantic label such as `Water Heater`
5. compare Monocle `data24` against live HA power sensors and refine naming/polling behavior

- Step 1 is still ready
- Step 5 is now partially implemented locally
- Steps 2-4 are still next after validating the new local changes

## Recommended next steps

1. Run `pytest` and a quick import/compile check on the new parsing/sensor changes
2. Commit and push `0.1.1`
3. Create GitHub tag/release `v0.1.1`
4. Update the HACS install in Home Assistant
5. Verify that the Catch Solar power entities now show `last_polled_at` every 60 seconds and report `unavailable` instead of stale `0` when Monocle omits a bucket value

## Home Assistant side context

- HACS has already installed `v0.1.0` from this public repo.
- The live config entry id is `01KW82PMQTTVX8AWT07PW40X49`.
- The current blocker is the HA 2026.6 options-flow/device-property collision fixed in this local patch.

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps. Example: `2026-06-29T08:25:00+10:00` maps to `1782685500000`.
- Home Assistant history showed the Catch Solar entities being re-polled every minute via `last_reported`, even when the upstream bucket had not changed.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site, so exposing the latest non-null fallback as the sensor state was misleading.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one, so naming should stay conservative and explicitly reference Monocle/raw telemetry rather than implying inverter-equivalent live power.
