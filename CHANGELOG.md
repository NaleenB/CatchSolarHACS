# Changelog

Implementation and installation details are in the [README](README.md).

## Unreleased

- Keep missing or malformed device state unknown instead of treating it as off;
  dynamically add relays discovered after startup.
- Add typed config-entry runtime data, checkpointed runtime persistence, polling
  gap diagnostics, coalesced token refresh, and safer live reconnect backoff.
- Redact identifying device/location fields from diagnostics.
- Make the HA-backed test suite fail fast when its harness is missing, enforce
  coverage, pin GitHub Actions, and add Dependabot/security-policy metadata.

## 0.2.0 — 2026-08-13

- Add optional read-only Socket.IO telemetry for near-real-time mains, solar,
  house, battery, channel, and controllable-device power and state.
- Add five `/data/datakwh` daily energy meters that are compatible with Home
  Assistant's Energy Dashboard: solar yield, grid import, grid export, house
  consumption, and consumed solar.
- Discover actor power/state and battery state-of-charge entities only when
  the upstream live event exposes them.
- Keep live and daily-energy availability independent from the existing
  primary-load polling and persisted runtime tracking.
- Add separate, default-off options for live telemetry and daily energy.
- Remove the obsolete `/data/data24` client, parser, option, tests, and three
  approximate Monocle power entities; migrate existing registry entries away.
- Publish only the newest live snapshot every five seconds to reduce Recorder
  and automation churn without reducing Socket.IO connection freshness.
- Poll optional daily-energy totals every five minutes instead of every minute
  to reduce load on the unofficial endpoint.
- Shut down daily-energy polling during unloads and rename the unverified
  `activeControlW` sensor to **Live Active Control**.
- Normalize solar and house power to positive magnitudes, discard unnamed
  `undefined` channels, and deduplicate repeated channels.
- Rename supplemental modules around their actual telemetry responsibility.
- Register both additions as experimental features in diagnostics and document
  their immediate-disable and permanent-removal boundaries.
- Credit Smatch Solar's MIT-licensed protocol work in
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## 0.1.7 — 2026-07-18

- Keep primary-load state available when location metadata or optional `data24`
  telemetry cannot be refreshed
- Restrict primary-load unavailability to failures of the actual device-state
  request

## 0.1.5 — 2026-06-29

- Add `icon.png` and `logo.png` for integration branding
- Convert icons to RGB for maximum Home Assistant compatibility
- Fix empty integration icon in Settings → Devices & Services
- Add `country: AU` to hacs.json for discoverability
- Add `async_setup` stub for HACS validation compliance
- Broaden mypy type-checking to all source files
- Sanitise test fixtures to use fake device/location IDs

## 0.1.4 — 2026-06-29

- Fix location primary-load label entities
- Add built-in primary-load runtime tracking with persisted state
- Add three location-level runtime sensors: 24h, 7d Rolling, Total
- Add config-entry removal cleanup for the persisted runtime store
- Semantic location and relay device naming
- Bundled local icon and logo SVG assets

## 0.1.3 — 2026-06-29

- Add runtime sensors and branding

## 0.1.2 — 2026-06-29

- Bump version

## 0.1.1 — 2026-06-28

- Fix HA 2026.6 config flow and entity collisions
- Clarify Monocle power feed behaviour
- Add primary load label option and tests
- Add reauth and diagnostics support

## 0.1.0 — 2026-06-28

- Initial Catch Solar HACS scaffold
