from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.salah_timetable.const import DOMAIN


async def test_create_and_duplicate(hass):
    data = {
        "name": " Test Mosque ",
        "mosque_id": " TEST ",
        "time_zone": "Europe/London",
    }
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Mosque"
    assert result["result"].unique_id == "test"
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
    )
    assert duplicate["type"] == FlowResultType.ABORT
    assert duplicate["reason"] == "already_configured"
    await hass.async_block_till_done()


async def test_invalid_input(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"name": " ", "mosque_id": "bad/id", "time_zone": "Mars/Olympus"},
    )
    assert result["errors"] == {
        "name": "invalid_name",
        "mosque_id": "invalid_mosque_id",
        "time_zone": "invalid_time_zone",
    }


async def test_options(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    assert result["type"] == FlowResultType.FORM
    bad = await hass.config_entries.options.async_configure(
        result["flow_id"], {"time_zone": "bad"}
    )
    assert bad["errors"] == {"time_zone": "invalid_time_zone"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"time_zone": "Asia/Riyadh"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {"time_zone": "Asia/Riyadh"}


async def test_config_flow_creates_loaded_entry_with_sensors(hass):
    """Creating a mosque through the UI flow loads its sensors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Integration Test Mosque",
            "mosque_id": "integration_test",
            "time_zone": "Europe/London",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    entry = result["result"]
    assert entry.domain == DOMAIN
    assert entry.unique_id == "integration_test"
    assert entry.title == "Integration Test Mosque"

    # Ensure setup has completed before inspecting the registries.
    await hass.async_block_till_done()

    if entry.state != ConfigEntryState.LOADED:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        "integration_test_fajr_begin",
    )

    assert entity_id is not None

    sensor = hass.states.get(entity_id)
    assert sensor is not None

    # No timetable has been imported yet.
    assert sensor.state == "unavailable"

    # Confirm the integration supports clean unloading.
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state == ConfigEntryState.NOT_LOADED
