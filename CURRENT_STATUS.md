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

## Current local-only work (not yet committed)

Release follow-up:

- bump integration version to `0.1.2`
- publish a fresh tag because `v0.1.1` already points at the earlier HA 2026.6 fix commit

Modified files:

- `CURRENT_STATUS.md`
- `custom_components/catchsolar/manifest.json`

Validation already run:

- `PYTHONPYCACHEPREFIX=/private/tmp/catchsolar-pyc python3 -m py_compile custom_components/catchsolar/*.py tests/*.py` passed
- `pytest` passed: `9 passed, 3 skipped`

## Status of paused work

User asked to continue the full rollout:

1. push a patch release
2. update HACS in live Home Assistant
3. verify the options flow with a semantic label such as `Water Heater`
4. verify the Monocle `data24` naming/null-handling/poll metadata on the live install

- Release commit `03fa9b1` is already on `main`
- A new version/tag is required because `v0.1.1` already exists on the previous release commit
- Live HACS update and verification are next

## Recommended next steps

1. Commit the `0.1.2` version bump
2. Push and create GitHub tag/release `v0.1.2`
3. Update the HACS install in Home Assistant
4. Verify that the Catch Solar power entities now show `last_polled_at` every 60 seconds and report `unknown`/no state instead of stale `0` when Monocle omits a bucket value

## Home Assistant side context

- HACS has already installed `v0.1.0` from this public repo.
- The live config entry id is `01KW82PMQTTVX8AWT07PW40X49`.
- `v0.1.1` is already published and maps to commit `1021b5f`.
- The Monocle telemetry cleanup is on commit `03fa9b1`, so it needs a new release tag.

## Monocle `data24` findings

- The live Monocle `data24` payload currently advances in 5-minute steps. Example: `2026-06-29T08:25:00+10:00` maps to `1782685500000`.
- Home Assistant history showed the Catch Solar entities being re-polled every minute via `last_reported`, even when the upstream bucket had not changed.
- The Monocle `Total Consumption` series is currently `null` in the latest live payload for this site, so exposing the latest non-null fallback as the sensor state was misleading.
- The Monocle power series do not cleanly match the live HA gold-standard sensors one-for-one, so naming should stay conservative and explicitly reference Monocle/raw telemetry rather than implying inverter-equivalent live power.
