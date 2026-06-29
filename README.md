# Catch Solar HACS

Home Assistant custom integration for [Catch Solar](https://catchpower.com.au) / The Monocle.

Catch Solar is an Australian solar energy monitoring system. The Monocle is the energy monitoring device that tracks your home's solar generation, consumption, and controlled loads (such as water heaters and pool pumps).

This integration connects to the Monocle API through Home Assistant's guided setup (config flow) and gives you:

- **Primary load state** — a binary sensor that shows whether your controlled load (e.g. water heater) is currently on or off, suitable for automations and dashboards
- **Runtime tracking** — three sensors that track how long your primary load has been running: today, the last 7 days, and all time since the integration was installed
- **Device monitoring** — online/offline status and metadata for each Monocle relay device
- **Power telemetry** — the latest 24-hour Monocle power-series values (approximate; see the [important warning](#important-warning) below)

No credentials belong in this repository. You enter your Catch Solar username and password during the guided setup inside Home Assistant, and Home Assistant stores them securely in the config entry.

## Important warning

The Monocle power sensors expose raw upstream `data24` bucketed values only.

- They are **not** directly usable as real-time household consumption, solar generation, or import/export truth.
- Treat them as approximate diagnostic telemetry, not canonical live power sensors.
- Do not assume one-to-one equivalence with inverter entities, utility-meter logic, or higher-frequency Home Assistant template or custom sensors.
- **`loadState`** (the on/off state Catch Solar reports for each monitored electrical load) remains the reliable Catch Solar signal for automations such as water-heater state tracking.
- The built-in runtime sensors are derived from the primary device `loadState`, not from Monocle power telemetry.

## What you get after installing

The integration creates two devices in Home Assistant:

| Device | What it represents |
|---|---|
| **Catch Solar Location** | Your Catch Solar / Monocle site |
| **Primary Load Relay** | The main controlled load (e.g. water heater relay) |

On the location device you will find:

- **Primary Load State** — binary sensor, on when your primary load is active
- **Primary Load Runtime 24h** — hours the load ran today (since midnight, local time)
- **Primary Load Runtime 7d Rolling** — hours the load ran in the last 7 days
- **Primary Load Runtime Total** — hours the load has run since the integration was installed
- **Monocle Solar Power** — latest 24h solar power value from Monocle (approximate)
- **Monocle Total Consumption Power** — latest 24h consumption value from Monocle (may be unavailable)
- **Monocle Export/Import Power** — latest 24h grid export/import value from Monocle (approximate)

On each relay device you will find diagnostic sensors for load state, online status, serial number, and device type.

Runtime history starts when this integration begins tracking. It is persisted by the integration and survives Home Assistant restarts (including when the primary load stays on across a restart). Runtime history is **not** reconstructed from Recorder or history data.

## Installation

1. In HACS, open the three-dot menu (top right) → **Custom repositories**.
2. Paste the repository URL: `https://github.com/NaleenB/CatchSolarHACS`
3. Select **Integration** as the category and click **Add**.
4. Find **Catch Solar** in the HACS integration list and click **Download**.
5. Restart Home Assistant when HACS prompts for it.
6. Go to **Settings → Devices & Services**, click **Add Integration**, and search for **Catch Solar**.
7. Enter your Catch Solar / Monocle username and password.
8. If you have more than one location on your account, select the one you want to add.

Validated on 2026-06-29 with Home Assistant OS `2026.6.4` and HACS `2.0.5`.

## Migrating from a manual YAML setup

If you were previously using a manual `command_line` sensor, template helpers, or other YAML-based entities for Catch Solar tracking, remove them before or after installing this integration. The integration provides its own runtime sensors that replace all of these.

In particular, remove from your Home Assistant configuration:

- Any `command_line` sensor polling the Monocle `/data/devices` endpoint
- Any `template` sensors or binary sensors that derive `loadState` from the raw sensor
- Any `utility_meter`, `integration` (Riemann sum), or `statistics` helpers that calculate runtime from the template sensors
- Any automations that reference the old entity IDs

Removing the Catch Solar config entry later (Settings → Devices & Services → Catch Solar → Remove) will automatically clean up the integration-managed devices, entities, and persisted runtime store.

## Uninstall / clean reinstall

For a clean reinstall, remove the Home Assistant config entry **before** removing the HACS package:

1. Go to **Settings → Devices & Services → Catch Solar** and remove the integration. This deletes the Catch Solar entities and devices and clears the persisted primary-load runtime store.
2. Go to HACS, find **Catch Solar**, open the three-dot menu, and select **Remove**.
3. Restart Home Assistant.
4. Reinstall from HACS and add the integration again (see [Installation](#installation)).

Removing the HACS package alone is **not** the clean-reset step. The config-entry removal is what clears the entities and the persisted runtime history.

## Options

After setup, click **Configure** on the Catch Solar integration tile to adjust:

| Option | Default | Description |
|---|---|---|
| **Scan interval** | 600 seconds | How often Home Assistant polls the Monocle API |
| **Enable power data** | On | Whether to fetch 24h Monocle power-series data (disable to reduce API calls) |
| **Primary load label** | `Primary Load` | A semantic name for your controlled load (e.g. `Water Heater`, `Pool Pump`). This label is used in entity and device names so you can identify them easily |

## Notes

- The integration uses the Monocle REST API at `https://monocle0.edde.world`. All requests go directly from your Home Assistant instance to that API.
- Polling interval and 24-hour power data are configurable in the integration options (see [Options](#options)).
- The runtime sensors use hours as their native unit and round to 2 decimal places.
- `Primary Load Runtime 24h` means local-calendar-day runtime since midnight, even though the entity name uses `24h`.
- Runtime state is persisted by the integration and survives restarts, including the case where the primary load stays on across a restart.
- A 60-second polling interval can still be useful: entity attributes include `last_polled_at` so Home Assistant shows successful refreshes even when the upstream 5-minute Monocle bucket has not changed yet.
- Device names include identifiers for debugging (e.g. `Catch Solar Location 99999`, `Water Heater Relay 88888`) rather than bare numeric names.
- If credentials expire or change, Home Assistant will prompt you for reauthentication through the config entry (no need to remove and re-add the integration).
- Diagnostics are shareable: sensitive values such as usernames, passwords, and tokens are automatically redacted.
- The Monocle `data24` feed advances in 5-minute steps, not second-by-second. It is upstream bucketed telemetry — the integration polls it, but the values reflect Monocle's aggregation, not live inverter readings.

## License

MIT — see [LICENSE](LICENSE).
