# CatchSolarHACS current status

Last updated: 2026-06-29

## Repo

- Local path: `/Users/naleen/coding_projects/CatchSolarHACS`
- GitHub: `NaleenB/CatchSolarHACS`
- Visibility: private

## Recent pushed work

- `274d052` — Initial Catch Solar HACS scaffold
- `6735b57` — Refine Catch Solar integration scaffold
- `dcd47a4` — Add reauth and diagnostics support

## Current local-only work (not yet committed)

Primary-entity model improvements plus semantic naming/options support:

- added location-level primary entities for stable dashboard/automation use
  - primary load-state binary sensor
  - primary raw load-state sensor
- kept per-device entities for diagnostics
- added options-flow support for a configurable primary load label, e.g. `Water Heater`
- location-level entity names now use that label
- added source-level tests for config flow and coordinator behavior
- updated README and option translations accordingly

Modified files:

- `CURRENT_STATUS.md`
- `README.md`
- `custom_components/catchsolar/binary_sensor.py`
- `custom_components/catchsolar/config_flow.py`
- `custom_components/catchsolar/const.py`
- `custom_components/catchsolar/entity.py`
- `custom_components/catchsolar/sensor.py`
- `custom_components/catchsolar/strings.json`
- `custom_components/catchsolar/translations/en.json`
- `tests/test_config_flow.py`
- `tests/test_coordinator.py`

Validation already run:

- `PYTHONPYCACHEPREFIX=/private/tmp/catchsolar-pyc python3 -m py_compile custom_components/catchsolar/*.py tests/*.py` passed
- `pytest` passed: `9 passed, 2 skipped`

## Status of paused work

User asked to do all three next steps:

1. commit the primary-entity model change
2. add coordinator/config-flow tests
3. refine naming further with an optional semantic alias, e.g. Water Heater

- Step 2 completed locally
- Step 3 completed locally
- Step 1 is next: commit this round

## Recommended next steps

1. Commit this round locally
2. User pushes from terminal:

```bash
cd /Users/naleen/coding_projects/CatchSolarHACS
git push origin main
```

## Important environment notes

- This Codex session cannot safely push using the pasted PAT and cannot reliably use the user's local keychain-backed git auth.
- The user can push successfully from their own terminal.
- Do not paste GitHub PATs into chat again.

## Home Assistant side context

- Live HA already has a YAML/secret-based Catch Solar polling path implemented separately from this repo.
- This repo is for the reusable HACS custom integration version.
