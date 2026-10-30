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
    assert result["result"].data["show_hijri_date"] is True
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
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Recovered Mosque", "mosque_id": "recovered", "time_zone": "UTC"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "recovered"
    assert result["result"].data["time_zone"] == "UTC"
    await hass.async_block_till_done()


async def test_options(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert "publication_profile" not in result["menu_options"]
    assert set(result["menu_options"]) >= {"import_url", "import_pdf", "import_csv"}
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
    assert entry.options["time_zone"] == "Asia/Riyadh"
    assert entry.options["show_hijri_date"] is True
    assert entry.options.get("completeness_required_fields", [
        "fajr_begin",
        "dhuhr_begin",
        "asr_begin",
        "maghrib_begin",
        "isha_begin",
    ]) == [
        "fajr_begin",
        "dhuhr_begin",
        "asr_begin",
        "maghrib_begin",
        "isha_begin",
    ]

async def test_hijri_mosque_setting_at_setup_and_afterwards(hass):
    initial = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    created = await hass.config_entries.flow.async_configure(
        initial["flow_id"],
        {
            "name": "Friday Mosque",
            "mosque_id": "friday",
            "time_zone": "Europe/London",
            "show_hijri_date": False,
        },
    )
    assert created["type"] == FlowResultType.CREATE_ENTRY
    entry = created["result"]
    assert entry.data["show_hijri_date"] is False
    settings = await hass.config_entries.options.async_init(entry.entry_id)
    settings = await hass.config_entries.options.async_configure(
        settings["flow_id"], {"next_step_id": "settings"}
    )
    assert settings["step_id"] == "settings"
    changed = await hass.config_entries.options.async_configure(
        settings["flow_id"], {"time_zone": "Europe/London", "show_hijri_date": True}
    )
    assert changed["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["show_hijri_date"] is True

    # An options change schedules an integration reload; wait for the new
    # coordinator to finish loading before testing its explicit shutdown.
    # Otherwise the HA 2026.10.3 timer-leak fixture may discover the
    # midnight callback left behind when this test tears down.
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    current = entry.runtime_data
    assert current._boundary_unsub is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state == ConfigEntryState.NOT_LOADED
    assert current._boundary_unsub is None


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


async def test_reconfigure_validates_fields_without_changing_identity(hass, entry):
    """Invalid reconfiguration keeps the same configured mosque."""
    original = dict(entry.data)
    start = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert start["type"] == FlowResultType.FORM
    assert start["step_id"] == "reconfigure"
    invalid = await hass.config_entries.flow.async_configure(
        start["flow_id"], {"name": " ", "time_zone": "Not/AZone"}
    )
    assert invalid["type"] == FlowResultType.FORM
    assert invalid["errors"] == {
        "name": "invalid_name",
        "time_zone": "invalid_time_zone",
    }
    assert entry.data == original
    assert entry.unique_id == "example"
    result = await hass.config_entries.flow.async_configure(
        invalid["flow_id"], {"name": "Recovered Mosque", "time_zone": "UTC"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "example"
    assert entry.data["mosque_id"] == "example"
    assert entry.data["name"] == "Recovered Mosque"
    assert entry.data["time_zone"] == "UTC"
    await hass.async_block_till_done()


async def test_reconfigure_preserves_mosque_storage_and_entity_ids(
    hass, populated, timetable
):
    """A renamed mosque uses the same entry, entities and approved source."""
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    old_runtime = populated.runtime_data
    old_unique_id = populated.unique_id

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": populated.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Renamed Mosque", "time_zone": "Asia/Riyadh"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert populated.title == "Renamed Mosque"
    assert populated.data["name"] == "Renamed Mosque"
    assert populated.data["mosque_id"] == "example"
    assert populated.data["time_zone"] == "Asia/Riyadh"
    assert populated.options["time_zone"] == "Asia/Riyadh"
    assert populated.unique_id == old_unique_id

    await hass.async_block_till_done()
    assert populated.state == ConfigEntryState.LOADED
    assert populated.runtime_data is not old_runtime
    assert populated.runtime_data.storage.timetables == (timetable,)
    assert (
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "example_fajr_begin")
        is not None
    )


async def test_settings_validate_and_save_completeness_required_fields(hass, entry):
    start = await hass.config_entries.options.async_init(entry.entry_id)
    settings = await hass.config_entries.options.async_configure(
        start["flow_id"], {"next_step_id": "settings"}
    )
    invalid = await hass.config_entries.options.async_configure(
        settings["flow_id"],
        {
            "time_zone": "Europe/London",
            "completeness_required_fields": [],
        },
    )
    assert invalid["type"] == FlowResultType.FORM
    assert invalid["errors"] == {
        "completeness_required_fields": "invalid_completeness_fields"
    }
    result = await hass.config_entries.options.async_configure(
        invalid["flow_id"],
        {
            "time_zone": "Europe/London",
            "completeness_required_fields": ["fajr_begin", "sunrise"],
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["completeness_required_fields"] == [
        "fajr_begin",
        "sunrise",
    ]
    await hass.async_block_till_done()
