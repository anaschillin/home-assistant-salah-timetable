"""Bounded CSV parsing with explicit date, column and time interpretation."""

import csv
import io
import re
import unicodedata
from collections.abc import Iterable
from datetime import date, time
from hashlib import sha256

from ..domain.model import DailyPrayers, PrayerField, Timetable, parse_time
from .import_model import (
    MAX_SOURCE_BYTES,
    ImportCandidate,
    ImportValidationError,
    build_coverage,
    coverage_warnings,
)

MAX_ROWS = 366
MAX_COLUMNS = 32
MAX_CELL_LENGTH = 256
DITTO_MARKERS = frozenset({'"', '""', "“", "”", "“”", "″"})


def suggest_approved_mapping(
    candidates: Iterable[ImportCandidate],
    headers: tuple[str, ...],
    kind: str,
    cross_year: bool,
) -> ImportCandidate | None:
    """Suggest a manual CSV mapping only when matching approvals agree.

    Header order can change, but every header must be present. Candidates
    already passed provenance validation when stored, including uniqueness and
    column-to-field validation. Pending proposals and URL sources are excluded.
    """
    matched = []
    for candidate in candidates:
        if (
            candidate.source_format != "csv"
            or candidate.source_url is not None
            or candidate.timetable.kind != kind
            or candidate.timetable.timetable_id.endswith("-cross-year") != cross_year
            or set(candidate.timetable.days[0].original) != set(headers)
        ):
            continue
        matched.append(candidate)
    if not matched:
        return None
    first = matched[0]
    signature = (first.date_column, first.time_format, dict(first.columns))
    if any(
        (candidate.date_column, candidate.time_format, dict(candidate.columns))
        != signature
        for candidate in matched[1:]
    ):
        return None
    return first


class CsvParser:
    """CSV adapter. No dates, AM/PM choices or missing times are guessed."""

    def _read(
        self, content: bytes
    ) -> tuple[str, tuple[str, ...], tuple[tuple[str, ...], ...]]:
        if (
            not isinstance(content, bytes)
            or not content
            or len(content) > MAX_SOURCE_BYTES
        ):
            raise ImportValidationError(
                "CSV must be nonempty and no larger than 512 KiB"
            )
        try:
            source_text = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise ImportValidationError("CSV must be UTF-8 encoded") from err
        if any(
            unicodedata.category(char) == "Cc" and char not in "\r\n\t"
            for char in source_text
        ):
            raise ImportValidationError("CSV contains unsupported control characters")
        try:
            reader = csv.reader(
                io.StringIO(source_text.removeprefix("\ufeff"), newline=""), strict=True
            )
            header = next(reader, None)
            if (
                not header
                or len(header) > MAX_COLUMNS
                or any(
                    not cell.strip()
                    or cell != cell.strip()
                    or len(cell) > MAX_CELL_LENGTH
                    for cell in header
                )
                or len(set(header)) != len(header)
            ):
                raise ImportValidationError(
                    "CSV needs 1–32 unique, nonempty column headers without surrounding spaces"
                )
            rows = []
            for row in reader:
                if not row:
                    continue
                if len(rows) >= MAX_ROWS:
                    raise ImportValidationError(
                        "CSV must contain no more than 366 dated rows"
                    )
                if len(row) != len(header):
                    raise ImportValidationError(
                        f"CSV row {len(rows) + 2} has the wrong number of cells"
                    )
                if any(len(cell) > MAX_CELL_LENGTH for cell in row):
                    raise ImportValidationError(
                        "CSV cells must contain no more than 256 characters"
                    )
                rows.append(tuple(row))
            if not rows:
                raise ImportValidationError(
                    "CSV must contain at least one dated prayer row"
                )
        except csv.Error as err:
            raise ImportValidationError(
                "CSV is malformed or contains an oversized field"
            ) from err
        return source_text, tuple(header), tuple(rows)

    def inspect(self, content: bytes) -> tuple[str, ...]:
        """Inspect bounds, CSV shape and encoding before displaying mapping choices."""
        return self._read(content)[1]

    def parse(
        self,
        content: bytes,
        *,
        timetable_id: str,
        kind: str,
        year: int,
        date_column: str,
        columns: dict[str, str],
        time_format: str = "24h",
    ) -> ImportCandidate:
        source_text, headers, rows = self._read(content)
        if type(year) is not int or not 1 <= year <= 9999:
            raise ImportValidationError("Enter a valid calendar year")
        cross_year = timetable_id == f"annual-{year}-cross-year" and kind == "annual"
        if cross_year and not 1900 <= year < 2199:
            raise ImportValidationError(
                "Cross-year imports require a first year from 1900 to 2198"
            )
        if time_format not in {"24h", "12h"}:
            raise ImportValidationError("Select either 24-hour or explicit AM/PM times")
        if date_column not in headers or date_column in columns or not columns:
            raise ImportValidationError(
                "Select a date column and at least one separate prayer column"
            )
        try:
            mapping = {name: PrayerField(value) for name, value in columns.items()}
        except (ValueError, TypeError, AttributeError) as err:
            raise ImportValidationError(
                "Select valid prayer fields for the CSV columns"
            ) from err
        if any(name not in headers for name in mapping) or len(
            set(mapping.values())
        ) != len(mapping):
            raise ImportValidationError(
                "Mapped prayer columns must exist and target distinct fields"
            )
        prior: dict[str, tuple[time, ...]] = {}
        parsed: list[DailyPrayers] = []
        previous_date = None
        for row_number, values in enumerate(rows, start=2):
            original = dict(zip(headers, values, strict=True))
            day_value = original[date_column].strip()
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day_value):
                    raise ValueError
                day = date.fromisoformat(day_value)
            except ValueError as err:
                raise ImportValidationError(
                    f"CSV row {row_number} needs a valid YYYY-MM-DD date"
                ) from err
            if day.year != year and not (cross_year and day.year == year + 1):
                raise ImportValidationError(
                    f"CSV row {row_number} does not match the declared year"
                )
            if previous_date is not None and day <= previous_date:
                raise ImportValidationError(
                    "CSV dates must be unique and in increasing order"
                )
            previous_date = day
            times = {}
            for column, field in mapping.items():
                value = original[column].strip()
                if not value:
                    prior.pop(column, None)
                    continue
                if value in DITTO_MARKERS:
                    if not field.value.endswith("_jamaat") or column not in prior:
                        raise ImportValidationError(
                            f"CSV row {row_number} has an unresolved quotation-mark Jamaat value"
                        )
                    times[field] = prior[column]
                    continue
                try:
                    parts = value.split(";") if field == PrayerField.JUMUAH else [value]
                    times[field] = tuple(
                        self._parse_time(part.strip(), time_format) for part in parts
                    )
                except ValueError as err:
                    raise ImportValidationError(
                        f"CSV row {row_number} has an invalid time; use the selected time format"
                    ) from err
                prior[column] = times[field]
            if not times:
                raise ImportValidationError(
                    f"CSV row {row_number} has no published prayer times in mapped columns"
                )
            try:
                parsed.append(DailyPrayers(day, times, original))
            except ValueError as err:
                raise ImportValidationError(
                    f"CSV row {row_number} has invalid or unordered congregation times"
                ) from err
        if cross_year:
            first, last = parsed[0].day, parsed[-1].day
            if (
                first.year != year
                or last.year != year + 1
                or (last - first).days >= 366
            ):
                raise ImportValidationError(
                    "Cross-year CSV must span the declared year and the following year within 366 days"
                )
        try:
            timetable = Timetable(timetable_id, kind, tuple(parsed))
        except ValueError as err:
            raise ImportValidationError(
                "Select a valid timetable identity and kind"
            ) from err
        coverage = build_coverage(timetable, year)
        if re.fullmatch(r"annual-[0-9]{4}-monthly-[0-9]{4}-[0-9]{4}", timetable_id):
            first, last = coverage.start_date, coverage.end_date
            expected = f"annual-{year}-monthly-{first:%m%d}-{last:%m%d}"
            if timetable_id != expected:
                raise ImportValidationError(
                    "This monthly URL source now covers different dates. Import the "
                    "new period as a separate source so older dates are preserved."
                )
        return ImportCandidate(
            timetable,
            source_text,
            sha256(content).hexdigest(),
            year,
            coverage_warnings(coverage),
            coverage,
            date_column=date_column,
            columns=columns,
            time_format=time_format,
        )

    @staticmethod
    def _parse_time(value: str, time_format: str) -> time:
        if time_format == "24h":
            return parse_time(value)
        if not re.fullmatch(r"(?:0[1-9]|1[0-2]):[0-5][0-9] (?:AM|PM)", value):
            raise ValueError("Use HH:MM AM/PM")
        hour = int(value[:2]) % 12 + (12 if value.endswith("PM") else 0)
        return time(hour, int(value[3:5]))
