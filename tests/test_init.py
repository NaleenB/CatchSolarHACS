from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.__init__ import async_remove_entry
from custom_components.catchsolar.const import DOMAIN


@pytest.mark.asyncio
async def test_remove_entry_deletes_runtime_store_from_loaded_tracker(hass) -> None:
    runtime_tracker = AsyncMock()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry-1"] = {"runtime_tracker": runtime_tracker}

    entry = SimpleNamespace(entry_id="entry-1")
    await async_remove_entry(hass, entry)

    runtime_tracker.async_delete.assert_awaited_once()
