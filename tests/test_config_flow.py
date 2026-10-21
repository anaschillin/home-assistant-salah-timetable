from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

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
