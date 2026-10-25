"""URL-first source setup, manual PDF fallback and update controls."""

from dataclasses import replace
from math import isfinite

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .download import DownloadError, async_download, validate_url
from .import_flow import CsvImportOptionsFlow, _safe_text
from .import_model import MAX_PDF_BYTES, ImportValidationError
from .pdf_parser import PdfParser
from .publication_profiles import PROFILES, publication_profile

PDF_LAYOUTS = [
    "nms_annual_v1",
    "nms_monthly_v1",
    "zak_annual_v1",
    "zak_ramadan_v1",
    "pdf_table_v1",
]


def _year(value) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or not 1900 <= value <= 2199
        or not float(value).is_integer()
    ):
        raise ImportValidationError("Year must be a whole number from 1900 to 2199")
    return int(value)


def read_uploaded_pdf(hass, file_id, layout_id):
    from homeassistant.components.file_upload import process_uploaded_file

    with process_uploaded_file(hass, file_id) as path:
        with path.open("rb") as stream:
            content = stream.read(MAX_PDF_BYTES + 1)
        parser = PdfParser(layout_id=layout_id)
        parser.inspect(content)
        return content


def source_fields(year, *, url=False):
    fields = {
        vol.Required("kind", default="annual"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["annual", "ramadan"], translation_key="timetable_kind"
            )
        ),
        vol.Required("year", default=year): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1900, max=2199, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required("pdf_layout", default="nms_annual_v1"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=PDF_LAYOUTS, translation_key="pdf_layout"
            )
        ),
    }
    if url:
        return {
            vol.Required("url"): selector.TextSelector(),
            vol.Required("media_type", default="pdf"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["pdf", "csv"], translation_key="source_format"
                )
            ),
            **fields,
        }
    return {
        vol.Required("file"): selector.FileSelector(
            selector.FileSelectorConfig(accept=".pdf,application/pdf")
        ),
        **fields,
    }


class ProfiledPdfParser(PdfParser):
    """Keep edition selection as metadata; leave extracted/published values intact."""

    def __init__(self, profile):
        super().__init__(layout_id=profile.layout_id)
        self.profile = profile

    def _csv(self, content):
        result = super()._csv(content)
        self.profile.validate_csv(result)
        return result

    def parse(self, content, **kwargs):
        candidate = super().parse(content, **kwargs)
        return replace(candidate, publication_profile_id=self.profile.profile_id)


class SourceOptionsFlow(CsvImportOptionsFlow):
    """All source formats reuse persisted staging and explicit review."""

    async def async_step_init(self, user_input=None):
        menu = [
            "import_url",
            "publication_profile",
            "import_pdf",
            "import_csv",
            "ramadan",
            "settings",
        ]
        coordinator = self._coordinator()
        if coordinator is not None:
            if coordinator.storage.staged is not None:
                menu.insert(0, "review")
            if coordinator.storage.remote_sources:
                menu.extend(["check_updates", "manage_sources"])
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_publication_profile(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        errors = {}
        detail = ""
        if user_input is not None:
            try:
                profile = publication_profile(user_input["profile_id"])
                if _year(user_input["year"]) != profile.year:
                    raise ImportValidationError(
                        f"This inspected edition is {profile.year}. Enter its printed Gregorian year."
                    )
                if coordinator.zone.key != profile.time_zone:
                    raise ImportValidationError(
                        f"This publication uses {profile.time_zone}; the mosque is configured for "
                        f"{coordinator.zone.key}. Review Mosque settings first. "
                        "The profile never changes your timezone automatically."
                    )
            except (ImportValidationError, KeyError) as err:
                errors["base"] = "invalid_publication_profile"
                detail = _safe_text(str(err))
            else:
                self._publication_profile = profile
                return await self.async_step_profile_pdf()
        return self.async_show_form(
            step_id="publication_profile",
            data_schema=vol.Schema(
                {
                    vol.Required("profile_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": profile.profile_id, "label": profile.title}
                                for profile in PROFILES.values()
                            ]
                        )
                    ),
                    vol.Required("year"): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1900,
                            max=2199,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "detail": detail,
                "mosque_timezone": coordinator.zone.key,
            },
        )

    async def async_step_profile_pdf(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        profile = getattr(self, "_publication_profile", None)
        if profile is None:
            return await self.async_step_publication_profile()
        errors = {}
        detail = ""
        if coordinator.zone.key != profile.time_zone:
            return await self.async_step_publication_profile()
        if user_input is not None:
            try:
                content = await self.hass.async_add_executor_job(
                    read_uploaded_pdf, self.hass, user_input["file"], profile.layout_id
                )
                parser = ProfiledPdfParser(profile)
                headers = await self.hass.async_add_executor_job(
                    parser.inspect, content
                )
            except (ValueError, OSError, HomeAssistantError) as err:
                errors["base"] = "invalid_pdf"
                detail = (
                    _safe_text(str(err))
                    if isinstance(err, ImportValidationError)
                    else "The uploaded PDF could not be read."
                )
            else:
                if self._coordinator() is not coordinator:
                    return self.async_abort(reason="integration_reloaded")
                self._content, self._headers = content, headers
                self._year, self._kind = profile.year, profile.kind
                self._parser, self._source_format, self._parser_id = (
                    parser,
                    "pdf",
                    profile.layout_id,
                )
                self._mapping_input = {
                    "date_column": profile.date_column,
                    "time_format": profile.time_format,
                    **{field: name for name, field in profile.columns.items()},
                }
                return await self.async_step_map_columns()
        return self.async_show_form(
            step_id="profile_pdf",
            data_schema=vol.Schema(
                {
                    vol.Required("file"): selector.FileSelector(
                        selector.FileSelectorConfig(accept=".pdf,application/pdf")
                    )
                }
            ),
            errors=errors,
            description_placeholders={"profile": profile.summary, "detail": detail},
        )

    async def async_step_map_columns(self, user_input=None):
        profile = getattr(self, "_publication_profile", None)
        coordinator = self._coordinator()
        if (
            profile is not None
            and coordinator is not None
            and coordinator.zone.key != profile.time_zone
        ):
            return await self.async_step_publication_profile(
                {"profile_id": profile.profile_id, "year": profile.year}
            )
        result = await super().async_step_map_columns(user_input)
        if profile is not None and result.get("step_id") == "map_columns":
            placeholders = result["description_placeholders"]
            placeholders["detail"] = (
                profile.summary + "\n\n" + placeholders.get("detail", "")
            )
        return result

    async def async_step_review(self, user_input=None):
        coordinator = self._coordinator()
        profile = None
        if coordinator is not None and coordinator.storage.staged is not None:
            profile_id = coordinator.storage.staged.candidate.publication_profile_id
            if profile_id is not None:
                profile = publication_profile(profile_id)
        wrong_timezone = (
            profile is not None and coordinator.zone.key != profile.time_zone
        )
        if (
            wrong_timezone
            and user_input is not None
            and user_input.get("decision") == "approve"
        ):
            user_input = None
        result = await super().async_step_review(user_input)
        if result.get("step_id") == "review":
            if wrong_timezone:
                result["errors"]["base"] = "invalid_publication_profile"
            if profile is not None:
                result["description_placeholders"]["summary"] = (
                    profile.summary
                    + "\n\n"
                    + result["description_placeholders"]["summary"]
                )
        return result

    async def async_step_import_url(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        errors = {}
        detail = ""
        if user_input is not None:
            try:
                year = _year(user_input["year"])
                url = validate_url(user_input["url"])
                result = await async_download(url, media_type=user_input["media_type"])
                if result.content is None:
                    raise ImportValidationError("The source returned no timetable")
                parser = (
                    PdfParser(layout_id=user_input["pdf_layout"])
                    if user_input["media_type"] == "pdf"
                    else self._csv_parser()
                )
                headers = await self.hass.async_add_executor_job(
                    parser.inspect, result.content
                )
            except DownloadError:
                errors["base"] = "source_failed"
                detail = "The download was blocked or failed. Use a public HTTPS URL without credentials, and check Home Assistant networking."
            except ImportValidationError as err:
                errors["base"] = "source_failed"
                detail = _safe_text(str(err))
            except (
                ValueError,
                OSError,
                HomeAssistantError,
            ):
                errors["base"] = "source_failed"
                detail = "Download or validation failed. Use a public HTTPS URL and a supported file/layout. The active timetable is unchanged."
            else:
                if self._coordinator() is not coordinator:
                    return self.async_abort(reason="integration_reloaded")
                self._content = result.content
                self._headers = headers
                self._year = year
                self._kind = user_input["kind"]
                self._parser = parser
                self._remote_url = url
                self._download_result = result
                self._source_format = user_input["media_type"]
                self._parser_id = (
                    user_input["pdf_layout"]
                    if self._source_format == "pdf"
                    else "csv_v1"
                )
                return await self.async_step_map_columns()
        return self.async_show_form(
            step_id="import_url",
            data_schema=vol.Schema(
                source_fields(
                    dt_util.utcnow().astimezone(coordinator.zone).year, url=True
                )
            ),
            errors=errors,
            description_placeholders={"detail": detail},
        )

    async def async_step_import_pdf(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        errors = {}
        detail = ""
        if user_input is not None:
            try:
                year = _year(user_input["year"])
                content = await self.hass.async_add_executor_job(
                    read_uploaded_pdf,
                    self.hass,
                    user_input["file"],
                    user_input["pdf_layout"],
                )
                parser = PdfParser(layout_id=user_input["pdf_layout"])
                headers = await self.hass.async_add_executor_job(
                    parser.inspect, content
                )
            except (ValueError, OSError, HomeAssistantError) as err:
                errors["base"] = "invalid_pdf"
                detail = (
                    _safe_text(str(err))
                    if isinstance(err, ImportValidationError)
                    else "The uploaded PDF could not be read."
                )
            else:
                self._content, self._headers = content, headers
                self._year, self._kind = year, user_input["kind"]
                self._parser, self._source_format, self._parser_id = (
                    parser,
                    "pdf",
                    user_input["pdf_layout"],
                )
                return await self.async_step_map_columns()
        return self.async_show_form(
            step_id="import_pdf",
            data_schema=vol.Schema(
                source_fields(dt_util.utcnow().astimezone(coordinator.zone).year)
            ),
            errors=errors,
            description_placeholders={"detail": detail},
        )

    async def async_step_check_updates(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if user_input is not None:
            await coordinator.source_updates.async_check_all()
            return self.async_abort(reason="checks_complete")
        return self.async_show_form(step_id="check_updates", data_schema=vol.Schema({}))

    async def async_step_manage_sources(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        sources = coordinator.storage.remote_sources
        if not sources:
            return self.async_abort(reason="no_remote_sources")
        if user_input is not None:
            source_id = user_input["source_id"]
            if user_input["action"] == "remove":
                try:
                    await coordinator.storage.async_remove_remote_source(source_id)
                except (
                    OSError,
                    HomeAssistantError,
                ):
                    return self.async_abort(reason="source_save_failed")
                coordinator.async_update_listeners()
            else:
                await coordinator.source_updates.async_check(source_id)
            return self.async_create_entry(
                title="", data=dict(self.config_entry.options)
            )
        status_lines = [
            f"{key}: {coordinator.storage.remote_checks.get(key, {}).get('status', 'configured')}"
            for key in sources
        ]
        return self.async_show_form(
            step_id="manage_sources",
            data_schema=vol.Schema(
                {
                    vol.Required("source_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=list(sources))
                    ),
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["check", "remove"], translation_key="source_action"
                        )
                    ),
                }
            ),
            description_placeholders={"summary": "\n\n".join(status_lines)},
        )
