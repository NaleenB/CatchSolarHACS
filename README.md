# Catch Solar HACS

Home Assistant custom integration for [Catch Solar](https://catchpower.com.au) / The Monocle.

Catch Solar is an Australian solar energy monitoring system. The Monocle is the energy monitoring device that tracks your home's solar generation, consumption, and controlled loads (such as water heaters and pool pumps).

This integration connects to the Monocle API through Home Assistant's guided setup (config flow) and gives you:

- **Primary load state** — a binary sensor that shows whether your controlled load (e.g. water heater) is currently on or off, suitable for automations and dashboards
- **Runtime tracking** — three sensors that track how long your primary load has been running: today, the last 7 days, and all time since the integration was installed
- **Device monitoring** — online/offline status and metadata for each Monocle relay device
- **Live power telemetry** — optional near-real-time mains, solar, house,
  battery, channel, and controllable-device values from Catch Power's
  Socket.IO feed
- **Energy Dashboard meters** — optional daily solar yield, grid import, grid
  export, house consumption, and consumed-solar totals

No credentials belong in this repository. You enter your Catch Solar username and password during the guided setup inside Home Assistant, and Home Assistant stores them securely in the config entry.

## Live-data note

Entities whose names start with **Live** use the Socket.IO stream used by the
Catch app. The integration receives every event but publishes only the newest
snapshot to Home Assistant once every five seconds. This keeps dashboards
responsive while limiting Recorder growth and automation churn.

The protocol is unofficial and reverse-engineered. Validate readings against
your installation before using them for safety-critical or high-cost
automations. `Live Mains Power` is positive while importing and negative while
exporting; solar and house power are exposed as positive magnitudes.

## What you get after installing

The integration initially creates two devices in Home Assistant and can add
controllable-device sub-devices when the live feed reports them:

| Device | What it represents |
|---|---|
| **Catch Solar Location** | Your Catch Solar / Monocle site |
| **Primary Load Relay** | The main controlled load (e.g. water heater relay) |

On the location device you will find:

- **Primary Load State** — binary sensor, on when your primary load is active
- **Primary Load Runtime 24h** — hours the load ran today (since midnight, local time)
- **Primary Load Runtime 7d Rolling** — hours the load ran in the last 7 days
- **Primary Load Runtime Total** — hours the load has run since the integration was installed
- **Live Mains Power** — positive when importing and negative when exporting
- **Live Solar Power** — current solar-generation magnitude
- **Live House Power** — current upstream household-load value
- **Live Battery Power** — raw upstream battery value, when available
- **Live Import Limit / Live Export Limit** — current site limits, when supplied
- **Daily Solar Yield**, **Daily Grid Import**, **Daily Grid Export**, **Daily
  House Consumption**, and **Daily Consumed Solar** — cumulative local-day kWh
  meters suitable for Home Assistant's Energy Dashboard

On each relay device you will find diagnostic sensors for load state, online status, serial number, and device type. Live events can also create nested devices for controllable actors, with power, state, and battery state-of-charge entities only when those fields exist upstream. Live channel power entities remain on the location device because channels do not have stable upstream IDs.

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

Validated on 2026-08-13 with Home Assistant `2026.7.4` and HACS `2.0.5`.

### Upgrading from 0.1.x

Version 0.2 removes the old five-minute `/data/data24` chart feed and its three
`Monocle * Power` entities. The config-entry migration automatically removes
their obsolete option and entity-registry entries. Primary-load state, runtime
history, devices, and entity IDs are preserved.

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
| **Scan interval** | 600 seconds | How often Home Assistant polls device and primary-load state |
| **Enable live data** | Off | Whether to subscribe to the read-only Socket.IO event stream |
| **Enable daily energy** | Off | Whether to poll local-day energy totals every 60 seconds |
| **Primary load label** | `Primary Load` | A semantic name for your controlled load (e.g. `Water Heater`, `Pool Pump`). This label is used in entity and device names so you can identify them easily |

### Experimental feature rollback

Live telemetry and daily energy are opt-in experimental features. To stop
them immediately without affecting primary-load state or runtime tracking,
turn off both corresponding options and submit the form. The integration
reloads automatically and stops their network activity.

The feature IDs, current enabled/loaded state, and latest update result appear
in downloaded integration diagnostics. The complete code inventory and
permanent-removal checklist are in
[`EXPERIMENTAL_FEATURES.md`](EXPERIMENTAL_FEATURES.md).

## Energy Dashboard setup

After the new daily meters have received their first update, go to **Settings
→ Dashboards → Energy → Configuration** and select:

- Solar production: **Daily Solar Yield**
- Grid consumption: **Daily Grid Import**
- Return to grid: **Daily Grid Export**

The meters reset at local midnight. Their `total_increasing` state class lets
Home Assistant handle that daily reset when building long-term statistics.

## Notes

- The integration uses the Monocle REST API at `https://monocle0.edde.world`. All requests go directly from your Home Assistant instance to that API.
- Primary-load state refreshes rely only on the device-state endpoint. Live and daily-energy failures do not make the load state unavailable.
- The polling interval applies only to device and primary-load state; live telemetry is pushed by Catch and published to Home Assistant every five seconds.
- The runtime sensors use hours as their native unit and round to 2 decimal places.
- `Primary Load Runtime 24h` means local-calendar-day runtime since midnight, even though the entity name uses `24h`.
- Runtime state is persisted by the integration and survives restarts, including the case where the primary load stays on across a restart.
- Device names include identifiers for debugging (e.g. `Catch Solar Location 99999`, `Water Heater Relay 88888`) rather than bare numeric names.
- If credentials expire or change, Home Assistant will prompt you for reauthentication through the config entry (no need to remove and re-add the integration).
- Diagnostics are shareable: sensitive values such as usernames, passwords, and tokens are automatically redacted.
- Live and daily-energy failures are isolated: neither can make primary-load
  state or runtime entities unavailable.
- This integration is read-only. It does not register Catch Power override or
  device-control services.

## Acknowledgements

Live Socket.IO telemetry, `/data/datakwh` energy support, and controllable
device discovery were informed by
[simonsays11/ha-smatch-solar](https://github.com/simonsays11/ha-smatch-solar).
Its MIT notice is retained in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## License

MIT — see [LICENSE](LICENSE).
