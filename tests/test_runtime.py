from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.runtime import PrimaryLoadRuntimeTracker, RuntimeState
from homeassistant.util import dt as dt_util


class _MemoryStore:
    def __init__(self, initial_data=None) -> None:
        self.data = initial_data
        self.saves: list[dict] = []

    async def async_load(self):
        return self.data

    async def async_save(self, payload):
        self.data = payload
        self.saves.append(payload)


def _tracker(initial_data=None) -> PrimaryLoadRuntimeTracker:
    tracker = PrimaryLoadRuntimeTracker(SimpleNamespace(), "test-entry")
    tracker._store = _MemoryStore(initial_data)
    return tracker


def _dt(value: str) -> datetime:
    parsed = dt_util.parse_datetime(value)
    assert parsed is not None
    return dt_util.as_utc(parsed)


@pytest.fixture(autouse=True)
def _brisbane_timezone():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(ZoneInfo("Australia/Brisbane"))
    yield
    dt_util.set_default_time_zone(original)


@pytest.mark.asyncio
async def test_runtime_accumulates_off_on_off_cycle() -> None:
    tracker = _tracker()

    await tracker.async_process(False, _dt("2026-06-29T00:00:00+00:00"))
    await tracker.async_process(True, _dt("2026-06-29T00:10:00+00:00"))
    snapshot = await tracker.async_process(False, _dt("2026-06-29T01:40:00+00:00"))

    assert snapshot.runtime_total_seconds == pytest.approx(5400)
    assert snapshot.runtime_24h_seconds == pytest.approx(5400)
    assert snapshot.runtime_7d_rolling_seconds == pytest.approx(5400)
    assert snapshot.primary_load_on is False


@pytest.mark.asyncio
async def test_runtime_recovers_across_restart_while_load_stays_on() -> None:
    tracker = _tracker(
        {
            "total_runtime_seconds": 0,
            "current_interval_start": "2026-06-29T00:10:00+00:00",
            "recent_intervals": [],
            "last_processed_at": "2026-06-29T00:40:00+00:00",
        }
    )

    snapshot = await tracker.async_process(True, _dt("2026-06-29T02:10:00+00:00"))

    assert snapshot.runtime_total_seconds == pytest.approx(7200)
    assert snapshot.primary_load_on is True


@pytest.mark.asyncio
async def test_runtime_24h_tracks_local_calendar_day_boundary() -> None:
    tracker = _tracker()

    await tracker.async_process(True, _dt("2026-06-29T13:30:00+00:00"))
    snapshot = await tracker.async_process(False, _dt("2026-06-29T14:30:00+00:00"))

    assert snapshot.runtime_total_seconds == pytest.approx(3600)
    assert snapshot.runtime_24h_seconds == pytest.approx(1800)


@pytest.mark.asyncio
async def test_runtime_7d_rolling_trims_old_intervals() -> None:
    tracker = _tracker()
    tracker._loaded = True
    tracker._state = RuntimeState.from_dict(
        {
            "total_runtime_seconds": 5 * 3600,
            "current_interval_start": None,
            "recent_intervals": [
                {
                    "start": "2026-06-20T00:00:00+00:00",
                    "end": "2026-06-20T02:00:00+00:00",
                },
                {
                    "start": "2026-06-26T00:00:00+00:00",
                    "end": "2026-06-26T03:00:00+00:00",
                },
            ],
            "last_processed_at": "2026-06-28T23:00:00+00:00",
        }
    )

    snapshot = await tracker.async_process(False, _dt("2026-06-29T00:00:00+00:00"))

    assert snapshot.runtime_total_seconds == pytest.approx(5 * 3600)
    assert snapshot.runtime_7d_rolling_seconds == pytest.approx(3 * 3600)
    assert len(tracker._state.recent_intervals) == 1


@pytest.mark.asyncio
async def test_runtime_total_persists_after_save_and_restore() -> None:
    tracker = _tracker()

    await tracker.async_process(True, _dt("2026-06-29T00:00:00+00:00"))
    await tracker.async_process(False, _dt("2026-06-29T01:30:00+00:00"))

    restored = _tracker(tracker._store.data)
    await restored.async_load()
    snapshot = restored.get_snapshot(_dt("2026-06-29T02:00:00+00:00"))

    assert snapshot.runtime_total_seconds == pytest.approx(5400)
    assert snapshot.runtime_24h_seconds == pytest.approx(5400)
