"""Native Home Assistant upload, column mapping and persisted import review."""

from collections import Counter
from dataclasses import replace
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

from ..domain.model import PrayerField, normalize_field
from ..parsers.csv_parser import CsvParser, suggest_approved_mapping
from ..parsers.import_model import MAX_SOURCE_BYTES, ImportValidationError
from ..persistence.storage import PendingImportError
from .import_preview import PDF_LAYOUT_LABELS as PDF_LAYOUT_LABELS
from .import_preview import _safe_text, import_summary as import_summary
from .import_review_flow import ImportReviewFlowMixin

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


class CsvImportOptionsFlow(ImportReviewFlowMixin, config_entries.OptionsFlow):
    """Reusable options-flow steps; settings are provided by the subclass."""

    def __init__(self) -> None:
        self._content: bytes | None = None
        self._headers: tuple[str, ...] = ()
        self._kind = "annual"
        self._monthly = False
        self._cross_year = False
        self._year: int | None = None
        self._review_stage_id: str | None = None
        self._mapping_input: dict[str, Any] = {}
        self._mapping_suggested = False
        self._review_runtime = None
        self._review_baseline = None
        self._review_page = 0
        self._review_canonical_only = False
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
                if user_input["kind"] not in {"annual", "ramadan", "cross_year"}:
                    raise ImportValidationError("Select a valid timetable type")
                self._cross_year = user_input["kind"] == "cross_year"
                self._kind = "annual" if self._cross_year else user_input["kind"]
                prior = suggest_approved_mapping(
                    coordinator.storage.approved_sources.values(),
                    self._headers,
                    self._kind,
                    self._cross_year,
                )
                self._mapping_suggested = prior is not None
                if prior is not None:
                    self._mapping_input = {
                        field.value: IGNORE_COLUMN for field in PrayerField
                    }
                    self._mapping_input.update(
                        {field: source for source, field in prior.columns.items()}
                    )
                    self._mapping_input.update(
                        date_column=prior.date_column, time_format=prior.time_format
                    )
                else:
                    self._mapping_input = {}
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
                            options=["annual", "ramadan", "cross_year"],
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
                timetable_id=(
                    f"annual-{self._year}-cross-year"
                    if self._cross_year
                    else f"{self._kind}-{self._year}"
                ),
                kind=self._kind,
                year=self._year,
                date_column=user_input["date_column"],
                columns=columns,
                time_format=user_input["time_format"],
            )
        )
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
            from ..sources.source_model import RemoteSource

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
        # Monthly identity and remote provenance preparation also await executor
        # work, so validate the runtime after all preparation and before writing.
        if self._coordinator() is not coordinator:
            return False
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
        detail = (
            "A previously approved manual CSV mapping is suggested. Check every "
            "column and the time format against this publication before continuing."
            if self._mapping_suggested
            else ""
        )
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

