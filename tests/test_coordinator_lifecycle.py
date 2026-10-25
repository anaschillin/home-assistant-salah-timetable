"""Coordinator timers must not survive unload, reload or setup failures."""

from datetime import datetime
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable import async_setup_entry, async_unload_entry


BOUNDARY = datetime.fromisoformat("2026-10-21T04:45:00+00:00")


async def test_unload_cancels_old_coordinator_boundary(hass, populated, freezer):
    freezer.move_to("2026-10-21T04:44:20+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    old = populated.runtime_data
    assert old._boundary_unsub is not None

    with patch.object(old, "_async_update_data", wraps=old._async_update_data) as update:
        assert await hass.config_entries.async_unload(populated.entry_id)
        assert old._boundary_unsub is None

        freezer.move_to(BOUNDARY)
        async_fire_time_changed(hass, BOUNDARY)
        await hass.async_block_till_done()
        update.assert_not_awaited()


async def test_repeated_reloads_leave_only_current_boundary(hass, populated, freezer):
    freezer.move_to("2026-10-21T04:44:20+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()

    retired = []
    for _ in range(3):
        retired.append(populated.runtime_data)
        assert retired[-1]._boundary_unsub is not None
        assert await hass.config_entries.async_reload(populated.entry_id)
        await hass.async_block_till_done()
        assert retired[-1]._boundary_unsub is None

    current = populated.runtime_data
    assert current not in retired
    assert current._boundary_unsub is not None
    with patch.object(
        current, "_async_update_data", wraps=current._async_update_data
    ) as current_update:
        freezer.move_to(BOUNDARY)
        async_fire_time_changed(hass, BOUNDARY)
        await hass.async_block_till_done()
        current_update.assert_awaited_once()
    assert current._boundary_unsub is not None


async def test_failed_platform_unload_preserves_running_coordinator(
    hass, populated, freezer
):
    freezer.move_to("2026-10-21T04:44:20+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    coordinator = populated.runtime_data

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        assert not await async_unload_entry(hass, populated)

    assert coordinator._boundary_unsub is not None
    assert coordinator.source_updates._started


async def test_failed_platform_setup_cleans_up_boundary(hass, populated, freezer):
    freezer.move_to("2026-10-21T04:44:20+00:00")

    with (
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=RuntimeError("test platform setup failure"),
        ),
        pytest.raises(RuntimeError, match="test platform setup failure"),
    ):
        await async_setup_entry(hass, populated)

    coordinator = populated.runtime_data
    assert coordinator._boundary_unsub is None
    assert coordinator.source_updates._stopped
