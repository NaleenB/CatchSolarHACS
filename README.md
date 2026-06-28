# Catch Solar HACS

Home Assistant custom integration for Catch Solar / The Monocle.

This integration connects to the Monocle API via a Home Assistant config flow and exposes:

- device load-state entities
- online/connectivity state
- device metadata sensors
- latest power-series values from the 24-hour API

No user credentials belong in this repository. Users enter their Catch Solar credentials in Home Assistant during setup; Home Assistant stores them in the config entry.

## Planned v1 entities

- binary sensor for device `loadState`
- binary sensor for device online status
- diagnostic sensors for serial, device type, channel types, and control flags
- sensors for latest:
  - Solar
  - Total Consumption
  - Export/Import

## Installation

Private bootstrap phase:

1. In HACS, add this repo as a custom repository.
2. Category: `Integration`
3. Install `Catch Solar HACS`
4. Restart Home Assistant
5. Add the integration from Settings → Devices & Services

## Setup

The config flow should:

1. prompt for Catch Solar username/password
2. authenticate against Monocle
3. fetch available locations
4. let the user select a location if multiple exist
5. create entities automatically

## Notes

- This repo intentionally contains no real Catch Solar usernames, passwords, tokens, or personal location metadata.
- `Export/Import` sign conventions may vary by upstream behavior and should be documented conservatively.
- Example runtime automations/helpers for water-heater tracking should live in docs, not as built-in integration behavior.
