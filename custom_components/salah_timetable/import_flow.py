"""Native Home Assistant upload, column mapping and persisted import review."""

from collections import Counter
from dataclasses import replace
from html import escape
from math import isfinite
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .csv_parser import CsvParser
from .import_comparison import (
    compare_import,
    comparison_overview,
    render_comparison_page,
)
from .import_model import MAX_SOURCE_BYTES, ImportValidationError
from .model import PrayerField, normalize_field
from .ramadan import RamadanSettings
from .ramadan_validation import ramadan_review
from .storage import PendingImportError, RamadanApprovalError, ReviewChangedError

PARSER = CsvParser()
IGNORE_COLUMN = "__ignore__"
MAX_UPLOAD_BYTES = MAX_SOURCE_BYTES


def read_uploaded_csv(hass: HomeAssistant, file_id: str) -> bytes:
    """Consume an opaque HA upload token, including cleanup, off the event loop."""
    with process_uploaded_file(hass, file_id) as path:
        with path.open("rb") as stream:
            content = stream.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ImportValidationError("CSV exceeds the 512 KiB import limit")
        PARSER.inspect(content)
        return content


def _safe_text(value: str) -> str:
    """Do not let imported labels become Markdown or HTML in the preview."""
    value = escape(value[:500])
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#"):
        value = value.replace(character, "\\" + character)
    return value.replace("\n", " ").replace("\r", " ")


PDF_LAYOUT_LABELS = {
    "pdf_table_v1": "Supported sample text-table PDF",
    "mosque_a_annual_v1": "Mosque A annual calendar",
    "mosque_a_monthly_v1": "Mosque A monthly calendar",
    "mosque_b_annual_v1": "Mosque B Masjid annual calendar",
    "mosque_b_ramadan_v1": "Mosque B Masjid separate Ramadan page",
}


def import_summary(candidate, existing, settings=None) -> str:
    """Bounded, explicit review of coverage, missing fields and replacement."""
    coverage = candidate.coverage
    table = candidate.timetable
    lines = [
        f"**{table.kind.title()} {candidate.year}** · {coverage.row_count} dated rows",
        f"Dates: {coverage.start_date.isoformat()} to {coverage.end_date.isoformat()}",
        f"SHA-256: `{candidate.sha256}`",
        f"Format: {candidate.time_format}. Date column: {_safe_text(candidate.date_column)}.",
        "Columns: "
        + "; ".join(
            f"{_safe_text(source)} → {field}"
            for source, field in candidate.columns.items()
        ),
        f"Missing dates{' within the supplied span' if table.kind == 'ramadan' else ''}: **{len(coverage.missing_dates)}**.",
    ]
    if candidate.source_format == "pdf":
        lines.append(
            "Recognized PDF: **"
            + PDF_LAYOUT_LABELS.get(candidate.parser_id, "Unsupported layout")
            + "**. Review the printed dates and every mapped prayer time."
        )
    if coverage.missing_fields:
        lines.append(
            "Fields absent from this source (number of rows): "
            + ", ".join(
                f"{key}: {count}" for key, count in coverage.missing_fields.items()
            )
        )
    previous = next(
        (item for item in existing if item.timetable_id == table.timetable_id), None
    )
    lines.append(
        f"Approval replaces **{len(previous.days)} existing rows** for this source."
        if previous
        else "Approval adds this source; other years remain stored."
    )
    lines.append(
        "Choose **Compare changes** to inspect every canonical and original-cell change "
        "before approval. The comparison never activates a pending import."
    )
    if table.kind == "ramadan":
        lines.append(
            "**Ramadan overrides apply only on confirmed dates or with explicit manual activation in Ramadan settings.**"
        )
    if candidate.parser_id in {"mosque_a_annual_v1", "mosque_a_monthly_v1"}:
        lines.append(
            "MOSQUE_A layout: morning/noon/evening columns are normalized to 24-hour time. "
            "The published Maghrib (Iftaar) value supplies both Jamaat and Iftar; Sunset remains Maghrib beginning. "
            "Friday's shared slot supplies Jumu'ah only. Second-Khutbah notes are not additional Jamaat events. "
            "Hijri dates do not confirm Ramadan activation."
        )
    if candidate.parser_id == "mosque_a_monthly_v1":
        lines.append(
            "MOSQUE_A monthly calendars may include dates outside Ramadan. "
            "The source date range does not confirm the Ramadan date window."
        )
    if candidate.parser_id == "mosque_b_ramadan_v1":
        lines.append(
            "Only the separate Mosque B Ramadan page is imported; annual pages are not imported. "
            "The printed table includes 20 March 2026 (Hijri 1 after Ramadan). "
            "Its 31 rows do not confirm 31 Ramadan dates. "
            "Maghrib beginning supplies default Iftar only when Ramadan is active. "
            "No Maghrib Jamaat, Jumu'ah or Taraweeh timestamp is supplied by this layout."
        )
    if candidate.parser_id == "mosque_b_annual_v1":
        lines.append(
            "Only Mosque B's twelve annual tables are imported; the separate Ramadan page is not imported. "
            "The clipped “May …” date cell is interpreted as **2026-05-01** only after checking "
            "the printed May 2026 heading, Friday weekday and complete sequence of dates 2–31. "
            "The original clipped date is retained. Check this interpretation before approval. "
            "Sehri is published only for February–May; other source months have no Sehri value. "
            "No Maghrib Jamaat, Iftar, Jumu'ah or Taraweeh timestamp is supplied by this layout. "
            "Friday's Zohar Jamaat column keeps its published meaning. "
            "May's Hijri caption is printed as 1446 AH; it is retained without changing the Gregorian 2026 dates. "
            "Printed Hijri headings do not confirm Ramadan dates."
        )
    lines.append("Preview (first three dates; all explicit times on those dates):")
    for row in table.days[:3]:
        values = "; ".join(
            f"{field.value}: {', '.join(value.strftime('%H:%M') for value in times)}"
            for field, times in row.times.items()
        )
        lines.append(f"- {row.day.isoformat()} — {values}")
    if candidate.warnings:
        lines.append("Validation warnings:")
        lines.extend(
            f"- {_safe_text(warning.replace('Missing times will remain unavailable.', 'Missing source fields remain absent from this import. Effective Ramadan availability is shown separately.'))}"
            for warning in candidate.warnings[:10]
        )
    settings = settings or RamadanSettings()
    if table.kind == "ramadan" or settings.mode == "on" or settings.confirmed_start:
        lines.append(ramadan_review(table, existing, settings))
    lines.append(
        "Approve only after checking these values against the published timetable."
    )
    return "\n\n".join(lines)


class CsvImportOptionsFlow(config_entries.OptionsFlow):
    """Reusable options-flow steps; settings are provided by the subclass."""

    def __init__(self) -> None:
        self._content: bytes | None = None
        self._headers: tuple[str, ...] = ()
        self._kind = "annual"
        self._monthly = False
        self._year: int | None = None
        self._review_stage_id: str | None = None
        self._mapping_input: dict[str, Any] = {}
        self._review_runtime = None
        self._review_baseline = None
        self._review_page = 0
        self._parser = PARSER
        self._source_format = "csv"
        self._parser_id = "csv_v1"
        self._remote_url = None
        self._download_result = None

    @staticmethod
    def _csv_parser():
        return CsvParser()

    def _coordinator(self):
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return None
        return self.config_entry.runtime_data

    async def async_step_init(self, user_input=None):
        menu = ["settings", "import_csv"]
        coordinator = self._coordinator()
        if coordinator is not None and coordinator.storage.staged is not None:
            menu.append("review")
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_import_csv(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if coordinator.storage.staged is not None:
            return self.async_abort(reason="pending_import_exists")
        errors = {}
        detail = ""
        if user_input is not None:
            try:
                year = user_input["year"]
                if (
                    isinstance(year, bool)
                    or not isinstance(year, (int, float))
                    or not isfinite(year)
                    or not 1900 <= year <= 2199
                    or not float(year).is_integer()
                ):
                    raise ImportValidationError(
                        "Year must be a whole number from 1900 to 2199"
                    )
                self._content = await self.hass.async_add_executor_job(
                    read_uploaded_csv, self.hass, user_input["file"]
                )
                self._headers = await self.hass.async_add_executor_job(
                    PARSER.inspect, self._content
                )
                self._year = int(user_input["year"])
                self._kind = user_input["kind"]
            except (ValueError, OSError, HomeAssistantError) as err:
                errors["base"] = "invalid_csv"
                detail = _safe_text(str(err))
            else:
                return await self.async_step_map_columns()
        return self.async_show_form(
            step_id="import_csv",
            data_schema=vol.Schema(
                {
                    vol.Required("file"): selector.FileSelector(
                        selector.FileSelectorConfig(accept=".csv,text/csv")
                    ),
                    vol.Required("kind", default="annual"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["annual", "ramadan"],
                            translation_key="timetable_kind",
                        )
                    ),
                    vol.Required(
                        "year",
                        default=dt_util.utcnow().astimezone(coordinator.zone).year,
                    ): selector.NumberSelector(
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
            description_placeholders={"detail": detail},
        )

    def _mapping_schema(self):
        source_options = [
            {"value": IGNORE_COLUMN, "label": "Do not import this field"}
        ] + [{"value": header, "label": header} for header in self._headers]
        inferred = {}
        for header in self._headers:
            try:
                inferred[header] = normalize_field(header)
            except ValueError:
                continue
        counts = Counter(inferred.values())
        schema = {
            vol.Required(
                "date_column",
                default=self._mapping_input.get(
                    "date_column",
                    next(
                        (
                            header
                            for header in self._headers
                            if header.lower() == "date"
                        ),
                        self._headers[0],
                    ),
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(self._headers))
            ),
            vol.Required(
                "time_format", default=self._mapping_input.get("time_format", "24h")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["24h", "12h"], translation_key="time_format"
                )
            ),
        }
        for field in PrayerField:
            suggested = next(
                (
                    header
                    for header, value in inferred.items()
                    if value == field and counts[value] == 1
                ),
                IGNORE_COLUMN,
            )
            schema[
                vol.Optional(
                    field.value, default=self._mapping_input.get(field.value, suggested)
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=source_options)
            )
        return vol.Schema(schema)

    @staticmethod
    def _selected_columns(user_input: dict) -> dict[str, str] | None:
        """Reject duplicate physical headers before starting any parser work."""
        columns = {}
        for field in PrayerField:
            source = user_input.get(field.value, IGNORE_COLUMN)
            if source == IGNORE_COLUMN:
                continue
            if source in columns or source == user_input["date_column"]:
                return None
            columns[source] = field.value
        return columns or None

    async def _stage_mapped_candidate(
        self, user_input: dict, columns: dict[str, str], coordinator
    ) -> bool:
        """Parse and stage without approving; return False if the runtime reloaded."""
        candidate = await self.hass.async_add_executor_job(
            lambda: self._parser.parse(
                self._content,
                timetable_id=f"{self._kind}-{self._year}",
                kind=self._kind,
                year=self._year,
                date_column=user_input["date_column"],
                columns=columns,
                time_format=user_input["time_format"],
            )
        )
        if self._coordinator() is not coordinator:
            return False
        if self._monthly:
            # Exact published spans coexist without removing another month's rows.
            first, last = candidate.coverage.start_date, candidate.coverage.end_date
            source_id = f"annual-{self._year}-monthly-{first:%m%d}-{last:%m%d}"
            candidate = await self.hass.async_add_executor_job(
                lambda: replace(
                    candidate,
                    timetable=replace(candidate.timetable, timetable_id=source_id),
                )
            )
        remote_source = None
        if self._remote_url is not None:
            from .source_model import RemoteSource

            candidate = await self.hass.async_add_executor_job(
                lambda: replace(
                    candidate,
                    source_url=self._remote_url,
                    etag=self._download_result.etag,
                    last_modified=self._download_result.last_modified,
                )
            )
            remote_source = RemoteSource(
                source_id=candidate.timetable.timetable_id,
                url=self._remote_url,
                media_type=self._source_format,
                kind=self._kind,
                year=self._year,
                date_column=user_input["date_column"],
                columns=columns,
                time_format=user_input["time_format"],
                parser_id=self._parser_id,
            )
        self._review_stage_id = await coordinator.storage.async_stage(
            candidate, remote_source=remote_source
        )
        coordinator.async_update_listeners()
        return True

    async def async_step_map_columns(self, user_input=None):
        if self._content is None:
            return self.async_abort(reason="upload_expired")
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        errors = {}
        detail = ""
        if user_input is not None:
            self._mapping_input = dict(user_input)
            columns = self._selected_columns(user_input)
            if columns is None:
                errors["base"] = "invalid_mapping"
            else:
                try:
                    if not await self._stage_mapped_candidate(
                        user_input, columns, coordinator
                    ):
                        return self.async_abort(reason="integration_reloaded")
                except PendingImportError:
                    return self.async_abort(reason="pending_import_exists")
                except ValueError as err:
                    errors["base"] = "invalid_csv"
                    detail = _safe_text(str(err))
                except OSError, HomeAssistantError:
                    errors["base"] = "save_failed"
                else:
                    self._content = None
                    return await self.async_step_review()
        return self.async_show_form(
            step_id="map_columns",
            data_schema=self._mapping_schema(),
            errors=errors,
            description_placeholders={"detail": detail},
        )

    def _review_source_context(self, candidate, coordinator):
        """Let source adapters validate the exact refreshed staged candidate."""
        return "", None

    async def async_step_review(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        errors = {}
        try:
            await coordinator.storage.async_load()
        except OSError, HomeAssistantError, ValueError, TypeError, KeyError:
            # Keep the pending proposal and last known comparison visible, but
            # never make a decision against an unreadable current store.
            errors["base"] = "save_failed"
            user_input = None
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        staged = coordinator.storage.staged
        if staged is None:
            return self.async_abort(reason="no_pending_import")
        if self._review_runtime is None:
            self._review_runtime = coordinator
        elif self._review_runtime is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        if self._review_stage_id is None:
            self._review_stage_id = staged.stage_id
        if self._review_stage_id != staged.stage_id:
            return self.async_abort(reason="stale_import")
        source_summary, source_error = self._review_source_context(
            staged.candidate, coordinator
        )
        if source_error is not None:
            errors["base"] = source_error
            if user_input is not None and user_input.get("decision") == "approve":
                user_input = None
        if user_input is not None:
            decision = user_input["decision"]
            if decision == "compare":
                self._review_page = 0
                return await self.async_step_compare()
            try:
                if decision == "approve":
                    if self._review_baseline is None:
                        raise ReviewChangedError("A comparison must be shown first")
                    await coordinator.storage.async_approve(
                        self._review_stage_id,
                        expected_baseline=self._review_baseline,
                    )
                    current = self._coordinator()
                    if current is not None:
                        await current.storage.async_load()
                        await current.async_refresh()
                        current.async_update_listeners()
                elif decision == "reject":
                    await coordinator.storage.async_reject(self._review_stage_id)
                    coordinator.async_update_listeners()
                else:
                    errors["base"] = "invalid_import_decision"
            except ReviewChangedError:
                self._review_page = 0
                errors["base"] = "review_changed"
            except RamadanApprovalError:
                errors["base"] = "ramadan_conflict"
            except ValueError:
                return self.async_abort(reason="stale_import")
            except (
                OSError,
                HomeAssistantError,
            ):
                errors["base"] = "save_failed"
            else:
                if decision in {"approve", "reject"}:
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options)
                    )
        tables = coordinator.storage.timetables
        baseline = coordinator.storage.review_baseline(
            staged.candidate.timetable.timetable_id
        )
        settings = RamadanSettings.from_options(self.config_entry.options)

        def render_review():
            comparison = compare_import(
                staged.candidate, baseline.timetable, baseline.source
            )
            summary = import_summary(staged.candidate, tables, settings)
            if source_summary:
                summary = source_summary + "\n\n" + summary
            return summary + "\n\n" + comparison_overview(comparison)

        summary = await self.hass.async_add_executor_job(render_review)
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        self._review_baseline = baseline
        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema(
                {
                    vol.Required("decision"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["compare", "approve", "reject"],
                            translation_key="import_decision",
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "summary": f"Mosque timezone: {coordinator.zone.key}\n\n" + summary
            },
        )

    async def async_step_compare(self, user_input=None):
        """Page through pending-source differences without changing active data."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if self._review_runtime is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        errors = {}
        try:
            await coordinator.storage.async_load()
        except OSError, HomeAssistantError, ValueError, TypeError, KeyError:
            errors["base"] = "save_failed"
            user_input = None
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        staged = coordinator.storage.staged
        if staged is None or staged.stage_id != self._review_stage_id:
            return self.async_abort(reason="stale_import")

        source_summary, source_error = self._review_source_context(
            staged.candidate, coordinator
        )
        if source_error is not None:
            errors["base"] = source_error
        baseline = coordinator.storage.review_baseline(
            staged.candidate.timetable.timetable_id
        )
        if self._review_baseline != baseline:
            self._review_page = 0
            errors.setdefault("base", "review_changed")
            user_input = None
        comparison = await self.hass.async_add_executor_job(
            compare_import, staged.candidate, baseline.timetable, baseline.source
        )
        if user_input is not None:
            action = user_input["action"]
            if action == "review":
                return await self.async_step_review()
            if action == "next":
                self._review_page += 1
            elif action == "previous":
                self._review_page -= 1
            else:
                errors["base"] = "invalid_import_decision"
        self._review_page = min(max(0, self._review_page), comparison.page_count() - 1)
        options = ["review"]
        if self._review_page > 0:
            options.append("previous")
        if self._review_page + 1 < comparison.page_count():
            options.append("next")
        detail = await self.hass.async_add_executor_job(
            render_comparison_page, comparison, self._review_page
        )
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        self._review_baseline = baseline
        if source_summary:
            detail = source_summary + "\n\n" + detail
        return self.async_show_form(
            step_id="compare",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            translation_key="import_compare_action",
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={"detail": detail},
        )
