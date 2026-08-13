# Experimental Feature Register

This register isolates the features introduced for Catch Solar `0.2.0`. They
do not participate in primary-load polling or runtime tracking and can be
disabled together without removing the integration.

| Feature ID | Home Assistant option | Runtime component | Entities | Introduced |
|---|---|---|---|---|
| `live_socketio_telemetry` | `enable_live_data` | `live_coordinator` / `live_client` | `Live *` site, actor, and channel sensors | `0.2.0` |
| `daily_energy_meters` | `enable_daily_energy` | `daily_energy_coordinator` | Five `Daily *` energy sensors | `0.2.0` |

The same IDs, enabled state, loaded state, and last-update result are included
in Home Assistant's downloadable integration diagnostics under
`experimental_features`.

## Immediate rollback

Open **Settings -> Devices & services -> Catch Solar -> Configure**, turn off
both **Enable live data** and **Enable daily energy**, and submit the form. The
config entry reloads automatically. This stops the Socket.IO connection and
daily-energy polling while leaving primary-load state and runtime tracking
active.

Home Assistant can retain entity-registry history for the disabled entities.
That is intentional: re-enabling a feature restores the same entity IDs. Remove
individual historical registry entries only after deciding not to re-enable
the feature.

## Code removal boundary

The experimental implementation is deliberately grouped in these locations:

- `custom_components/catchsolar/supplemental.py`: live client and supplemental
  coordinators
- `custom_components/catchsolar/supplemental_sensor.py`: all live and daily
  entities and discovery
- `custom_components/catchsolar/parsing.py`: functions named
  `extract_daily_energy` and `extract_live_event`, plus their private helpers
- `custom_components/catchsolar/api.py`: access-token helper and
  `async_get_daily_energy`
- `custom_components/catchsolar/__init__.py`: optional startup and shutdown
  wiring
- `custom_components/catchsolar/const.py`, `config_flow.py`, `strings.json`, and
  `translations/en.json`: the two feature options and tracking metadata
- `custom_components/catchsolar/manifest.json`: `python-socketio` dependency
- `tests/test_supplemental.py`, the supplemental parser/entity tests, and the
  `0.2.0` documentation

For a permanent removal, disable both options first, then revert the dedicated
feature commit or remove the locations above as one change. Run the full test
suite afterward. Keep `THIRD_PARTY_NOTICES.md` if any adapted Smatch Solar code
or protocol work remains; it can be removed only when none remains.

## Promotion criteria

Do not remove the experimental label until both features have run reliably on
the target Home Assistant installation and their values have been compared
with known-good sources across normal operation, API errors, reconnects, and a
local-midnight daily reset.
