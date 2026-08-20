from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_STORAGE_VERSION = 1
_RECENT_INTERVAL_RETENTION = timedelta(days=8)
_TRAILING_WINDOW = timedelta(days=7)
_CHECKPOINT_INTERVAL = timedelta(minutes=15)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return dt_util.as_utc(parsed)


def _serialize_datetime(value: datetime | None) -> str | None:
    return dt_util.as_utc(value).isoformat() if value is not None else None


def _coerce_runtime_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)
    return 0.0


def _interval_overlap_seconds(
    start: datetime, end: datetime, window_start: datetime, window_end: datetime
) -> float:
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    return max((overlap_end - overlap_start).total_seconds(), 0.0)


@dataclass(slots=True)
class RuntimeInterval:
    start: datetime
    end: datetime

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RuntimeInterval | None:
        start = _parse_datetime(payload.get("start"))
        end = _parse_datetime(payload.get("end"))
        if start is None or end is None or end <= start:
            return None
        return cls(start=start, end=end)

    def as_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


@dataclass(slots=True)
class RuntimeSnapshot:
    runtime_24h_seconds: float
    runtime_7d_rolling_seconds: float
    runtime_total_seconds: float
    current_interval_start: datetime | None
    last_processed_at: datetime | None
    primary_load_on: bool
    data_gap_seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_24h_seconds": self.runtime_24h_seconds,
            "runtime_7d_rolling_seconds": self.runtime_7d_rolling_seconds,
            "runtime_total_seconds": self.runtime_total_seconds,
            "current_interval_start": _serialize_datetime(self.current_interval_start),
            "last_processed_at": _serialize_datetime(self.last_processed_at),
            "primary_load_on": self.primary_load_on,
            "data_gap_seconds": self.data_gap_seconds,
        }


@dataclass(frozen=True, slots=True)
class RuntimeTarget:
    location_id: int
    primary_device_id: int

    @classmethod
    def from_dict(cls, payload: Any) -> RuntimeTarget | None:
        if not isinstance(payload, dict):
            return None
        location_id = payload.get("location_id")
        primary_device_id = payload.get("primary_device_id")
        if isinstance(location_id, bool) or not isinstance(location_id, int):
            return None
        # A target without a resolved primary relay is not an identity. Treat
        # older/transient records containing null as legacy state instead.
        if isinstance(primary_device_id, bool) or not isinstance(primary_device_id, int):
            return None
        return cls(location_id, primary_device_id)

    def as_dict(self) -> dict[str, int]:
        return {
            "location_id": self.location_id,
            "primary_device_id": self.primary_device_id,
        }


@dataclass(slots=True)
class RuntimeState:
    total_runtime_seconds: float = 0.0
    current_interval_start: datetime | None = None
    recent_intervals: list[RuntimeInterval] = field(default_factory=list)
    last_processed_at: datetime | None = None
    target: RuntimeTarget | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> RuntimeState:
        if not isinstance(payload, dict):
            return cls()

        intervals: list[RuntimeInterval] = []
        for item in payload.get("recent_intervals", []):
            if not isinstance(item, dict):
                continue
            interval = RuntimeInterval.from_dict(item)
            if interval is not None:
                intervals.append(interval)

        current_interval_start = _parse_datetime(payload.get("current_interval_start"))
        last_processed_at = _parse_datetime(payload.get("last_processed_at"))
        if (
            current_interval_start
            and last_processed_at
            and current_interval_start > last_processed_at
        ):
            last_processed_at = current_interval_start

        return cls(
            total_runtime_seconds=_coerce_runtime_seconds(payload.get("total_runtime_seconds")),
            current_interval_start=current_interval_start,
            recent_intervals=intervals,
            last_processed_at=last_processed_at,
            target=RuntimeTarget.from_dict(payload.get("target")),
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "total_runtime_seconds": self.total_runtime_seconds,
            "current_interval_start": _serialize_datetime(self.current_interval_start),
            "recent_intervals": [interval.as_dict() for interval in self.recent_intervals],
            "last_processed_at": _serialize_datetime(self.last_processed_at),
        }
        if self.target is not None:
            payload["target"] = self.target.as_dict()
        return payload


class PrimaryLoadRuntimeTracker:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.primary_load_runtime",
        )
        self._state = RuntimeState()
        self._loaded = False
        self._last_persisted_at: datetime | None = None
        self._last_data_gap_seconds = 0.0

    async def async_load(self, target: RuntimeTarget | None = None) -> None:
        if self._loaded:
            if target is not None:
                await self._async_prepare_target(target)
            return
        self._state = RuntimeState.from_dict(await self._store.async_load())
        self._loaded = True
        self._last_persisted_at = self._state.last_processed_at
        if target is not None:
            await self._async_prepare_target(target)

    async def async_delete(self) -> None:
        self._state = RuntimeState()
        self._loaded = True
        self._last_persisted_at = None
        await self._store.async_remove()

    async def async_process(
        self,
        load_is_on: bool,
        now: datetime | None = None,
        target: RuntimeTarget | None = None,
    ) -> RuntimeSnapshot:
        await self.async_load(target)

        processed_at = dt_util.as_utc(now or dt_util.utcnow())
        if (
            self._state.last_processed_at is not None
            and processed_at < self._state.last_processed_at
        ):
            processed_at = self._state.last_processed_at

        previous_interval_start = self._state.current_interval_start
        previous_total = self._state.total_runtime_seconds
        previous_interval_count = len(self._state.recent_intervals)
        previous_processed_at = self._state.last_processed_at
        if previous_processed_at is None:
            self._last_data_gap_seconds = 0.0
        else:
            elapsed = (processed_at - previous_processed_at).total_seconds()
            self._last_data_gap_seconds = (
                elapsed if elapsed > _CHECKPOINT_INTERVAL.total_seconds() * 2 else 0.0
            )

        if self._state.current_interval_start is None:
            if load_is_on:
                self._state.current_interval_start = processed_at
        elif not load_is_on:
            interval = RuntimeInterval(
                start=self._state.current_interval_start,
                end=processed_at,
            )
            self._state.total_runtime_seconds += max(
                (interval.end - interval.start).total_seconds(),
                0.0,
            )
            self._state.recent_intervals.append(interval)
            self._state.current_interval_start = None

        self._state.last_processed_at = processed_at
        self._trim_recent_intervals(processed_at)
        state_changed = (
            previous_interval_start != self._state.current_interval_start
            or previous_total != self._state.total_runtime_seconds
            or previous_interval_count != len(self._state.recent_intervals)
        )
        checkpoint_due = (
            self._last_persisted_at is None
            or processed_at - self._last_persisted_at >= _CHECKPOINT_INTERVAL
        )
        if state_changed or previous_processed_at is None or checkpoint_due:
            await self._store.async_save(self._state.as_dict())
            self._last_persisted_at = processed_at
        return self.get_snapshot(processed_at)

    async def _async_prepare_target(self, target: RuntimeTarget) -> None:
        if self._state.target == target:
            return

        if self._state.target is not None:
            self._state = RuntimeState(target=target)
            self._last_persisted_at = None
            self._last_data_gap_seconds = 0.0
        else:
            # Stores created before target metadata was introduced retain their
            # history and adopt the current target on first load.
            self._state.target = target

        await self._store.async_save(self._state.as_dict())
        self._last_persisted_at = self._state.last_processed_at

    def get_snapshot(
        self,
        now: datetime | None = None,
        *,
        extrapolate_current_interval: bool = True,
    ) -> RuntimeSnapshot:
        processed_at = dt_util.as_utc(now or dt_util.utcnow())
        if (
            self._state.last_processed_at is not None
            and processed_at < self._state.last_processed_at
        ):
            processed_at = self._state.last_processed_at

        data_gap_seconds = self._last_data_gap_seconds
        if not extrapolate_current_interval and self._state.last_processed_at is not None:
            data_gap_seconds = max(
                (processed_at - self._state.last_processed_at).total_seconds(),
                0.0,
            )
            processed_at = self._state.last_processed_at

        trailing_window_start = processed_at - _TRAILING_WINDOW
        local_now = dt_util.as_local(processed_at)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_day_start = dt_util.as_utc(local_midnight)

        runtime_24h_seconds = 0.0
        runtime_7d_seconds = 0.0
        for interval in self._state.recent_intervals:
            runtime_24h_seconds += _interval_overlap_seconds(
                interval.start, interval.end, local_day_start, processed_at
            )
            runtime_7d_seconds += _interval_overlap_seconds(
                interval.start, interval.end, trailing_window_start, processed_at
            )

        runtime_total_seconds = self._state.total_runtime_seconds
        current_interval_start = self._state.current_interval_start
        if current_interval_start is not None:
            runtime_total_seconds += max(
                (processed_at - current_interval_start).total_seconds(),
                0.0,
            )
            runtime_24h_seconds += _interval_overlap_seconds(
                current_interval_start, processed_at, local_day_start, processed_at
            )
            runtime_7d_seconds += _interval_overlap_seconds(
                current_interval_start, processed_at, trailing_window_start, processed_at
            )

        return RuntimeSnapshot(
            runtime_24h_seconds=runtime_24h_seconds,
            runtime_7d_rolling_seconds=runtime_7d_seconds,
            runtime_total_seconds=runtime_total_seconds,
            current_interval_start=current_interval_start,
            last_processed_at=self._state.last_processed_at,
            primary_load_on=current_interval_start is not None,
            data_gap_seconds=data_gap_seconds,
        )

    def _trim_recent_intervals(self, now: datetime) -> None:
        cutoff = now - _RECENT_INTERVAL_RETENTION
        self._state.recent_intervals = [
            interval for interval in self._state.recent_intervals if interval.end > cutoff
        ]
