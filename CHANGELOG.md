# Changelog

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
