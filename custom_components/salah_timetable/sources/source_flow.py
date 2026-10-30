"""URL-first source setup, manual PDF fallback and update controls."""

from math import isfinite

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from ..imports.import_flow import PDF_LAYOUT_LABELS, CsvImportOptionsFlow, _safe_text
from ..parsers.import_model import MAX_PDF_BYTES, ImportValidationError
from ..parsers.pdf_parser import PdfParser
from .download import DownloadError, async_download, validate_url


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


def read_uploaded_pdf(hass, file_id):
    """Consume the one-use upload; the caller validates/detects its PDF type."""
    from homeassistant.components.file_upload import process_uploaded_file

    with process_uploaded_file(hass, file_id) as path:
        with path.open("rb") as stream:
            return stream.read(MAX_PDF_BYTES + 1)


def canonical_kind(import_type: str) -> str:
    """Monthly coverage is stored as a partial annual source, never a third kind."""
    if import_type not in {"annual", "monthly", "ramadan"}:
        raise ImportValidationError("Choose Annual, Monthly or Ramadan")
    return "ramadan" if import_type == "ramadan" else "annual"


def source_fields(year, *, url=False):
    fields = {
        vol.Required("kind", default="annual"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["annual", "monthly", "ramadan"],
                translation_key="timetable_kind",
            )
        ),
        vol.Required("year", default=year): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1900, max=2199, step=1, mode=selector.NumberSelectorMode.BOX
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


class SourceOptionsFlow(CsvImportOptionsFlow):
    """All source formats reuse persisted staging and explicit review."""

    async def async_step_init(self, user_input=None):
        menu = [
            "import_url",
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
                if self._rollover_sources(coordinator):
                    menu.append("annual_rollover")
        return self.async_show_menu(step_id="init", menu_options=menu)

    @staticmethod
    def _rollover_sources(coordinator) -> dict:
        """Only fully approved annual URL publications can seed the next year."""
        return {
            key: source
            for key, source in coordinator.storage.remote_sources.items()
            if source.kind == "annual"
            and source.year < 2199
            and key == f"annual-{source.year}"
            and key in coordinator.storage.approved_sources
            and any(
                table.timetable_id == key and len(table.days) >= 300
                for table in coordinator.storage.timetables
            )
        }

    async def async_step_annual_rollover(self, user_input=None):
        """Guide a new year's URL through the *existing* approval process.

        Never invent the publisher URL, reuse previous-year data or approve a
        new source automatically. Next year remains a distinct source identity.
        """
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        candidates = self._rollover_sources(coordinator)
        if not candidates:
            return self.async_abort(reason="no_rollover_sources")
        errors = {}
        if user_input is not None:
            original = candidates.get(user_input["source_id"])
            if original is None:
                errors["base"] = "invalid_rollover"
            else:
                following = original.year + 1
                if any(
                    table.kind == "annual"
                    and any(row.day.year == following for row in table.days)
                    for table in coordinator.storage.timetables
                ):
                    errors["base"] = "rollover_already_approved"
                elif f"annual-{following}" in coordinator.storage.remote_sources:
                    errors["base"] = "rollover_already_configured"
                else:
                    # Reuse the import's HTTPS validation, bounded downloader,
                    # strict PDF/CSV recognition and review staging.
                    return await self.async_step_import_url(
                        {
                            "year": following,
                            "kind": "annual",
                            "media_type": original.media_type,
                            "url": user_input["url"],
                        }
                    )
        return self.async_show_form(
            step_id="annual_rollover",
            data_schema=vol.Schema(
                {
                    vol.Required("source_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=key,
                                    label=f"{key}: {source.year} → {source.year + 1}",
                                )
                                for key, source in candidates.items()
                            ]
                        )
                    ),
                    vol.Required("url"): selector.TextSelector(),
                }
            ),
            errors=errors,
        )

    async def _inspect_source(self, content, *, media_type, import_type):
        """Share PDF/CSV preparation without changing the review or approval flow."""
        parser = (
            PdfParser(layout_id="auto", import_type=import_type)
            if media_type == "pdf"
            else self._csv_parser()
        )
        headers = await self.hass.async_add_executor_job(parser.inspect, content)
        return parser, headers

    async def async_step_map_columns(self, user_input=None):
        result = await super().async_step_map_columns(user_input)
        if result.get("step_id") == "map_columns":
            placeholders = result["description_placeholders"]
            parser = getattr(self, "_parser", None)
            if isinstance(parser, PdfParser):
                detected = PDF_LAYOUT_LABELS.get(parser.layout_id, "Unknown PDF layout")
                placeholders["detail"] = (
                    f"Recognized PDF: **{detected}**. Confirm the printed year, "
                    "date coverage and mapped columns before approval.\n\n"
                    + placeholders.get("detail", "")
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
                kind = canonical_kind(user_input["kind"])
                url = validate_url(user_input["url"])
                result = await async_download(url, media_type=user_input["media_type"])
                if result.content is None:
                    raise ImportValidationError("The source returned no timetable")
                parser, headers = await self._inspect_source(
                    result.content,
                    media_type=user_input["media_type"],
                    import_type=user_input["kind"],
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
                self._kind = kind
                self._monthly = user_input["kind"] == "monthly"
                self._parser = parser
                self._remote_url = url
                self._download_result = result
                self._source_format = user_input["media_type"]
                self._parser_id = (
                    parser.layout_id if self._source_format == "pdf" else "csv_v1"
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
                kind = canonical_kind(user_input["kind"])
                content = await self.hass.async_add_executor_job(
                    read_uploaded_pdf,
                    self.hass,
                    user_input["file"],
                )
                parser, headers = await self._inspect_source(
                    content, media_type="pdf", import_type=user_input["kind"]
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
                self._year, self._kind = year, kind
                self._monthly = user_input["kind"] == "monthly"
                self._parser, self._source_format, self._parser_id = (
                    parser,
                    "pdf",
                    parser.layout_id,
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
                coordinator.source_updates.source_profiles_changed()
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
