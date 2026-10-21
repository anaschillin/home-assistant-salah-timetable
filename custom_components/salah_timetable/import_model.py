"""Immutable import candidates, provenance and explicit coverage reports."""

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping, Protocol

from .model import PrayerField, Timetable

MAX_SOURCE_BYTES = 512 * 1024


class ImportValidationError(ValueError):
    """An actionable, safe error suitable for showing in an import flow."""


@dataclass(frozen=True)
class ImportCoverage:
    """Coverage of source rows, never inferred prayer values."""

    start_date: date
    end_date: date
    row_count: int
    missing_dates: tuple[date, ...]
    missing_fields: Mapping[str, int]

    def __post_init__(self) -> None:
        if (
            type(self.start_date) is not date
            or type(self.end_date) is not date
            or self.start_date > self.end_date
            or type(self.row_count) is not int
            or not 1 <= self.row_count <= 366
        ):
            raise ImportValidationError("Invalid import coverage")
        missing_dates = tuple(self.missing_dates)
        if (
            any(type(day) is not date for day in missing_dates)
            or tuple(sorted(set(missing_dates))) != missing_dates
            or len(missing_dates) > 366
        ):
            raise ImportValidationError("Invalid missing-date report")
        missing_fields = dict(self.missing_fields)
        for field, count in missing_fields.items():
            PrayerField(field)
            if type(count) is not int or not 1 <= count <= self.row_count:
                raise ImportValidationError("Invalid missing-field report")
        object.__setattr__(self, "missing_dates", missing_dates)
        object.__setattr__(self, "missing_fields", MappingProxyType(missing_fields))

    def as_dict(self) -> dict:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "row_count": self.row_count,
            "missing_dates": [day.isoformat() for day in self.missing_dates],
            "missing_fields": dict(self.missing_fields),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImportCoverage":
        return cls(
            date.fromisoformat(data["start_date"]),
            date.fromisoformat(data["end_date"]),
            data["row_count"],
            tuple(date.fromisoformat(day) for day in data["missing_dates"]),
            data["missing_fields"],
        )


def build_coverage(timetable: Timetable, year: int) -> ImportCoverage:
    """Count exact missing dates/fields for the declared source kind."""
    days = tuple(row.day for row in timetable.days)
    first, last = min(days), max(days)
    start = date(year, 1, 1) if timetable.kind == "annual" else first
    end = date(year, 12, 31) if timetable.kind == "annual" else last
    present = set(days)
    missing_dates = tuple(
        start + timedelta(days=offset)
        for offset in range((end - start).days + 1)
        if start + timedelta(days=offset) not in present
    )
    missing_fields = {
        field.value: count
        for field in PrayerField
        if (count := sum(field not in row.times for row in timetable.days))
    }
    return ImportCoverage(first, last, len(days), missing_dates, missing_fields)


def coverage_warnings(coverage: ImportCoverage) -> tuple[str, ...]:
    """Generate deterministic, bounded warnings with no source-controlled text."""
    warnings = []
    if coverage.missing_dates:
        warnings.append(
            f"{len(coverage.missing_dates)} dates are missing from this timetable's coverage."
        )
    if coverage.missing_fields:
        warnings.append(
            "Some prayer fields are missing. Missing times will remain unavailable."
        )
    return tuple(warnings)


@dataclass(frozen=True)
class ImportCandidate:
    """Source and parsed data staged for approval, not yet effective."""

    timetable: Timetable
    source_text: str
    sha256: str
    year: int
    warnings: tuple[str, ...]
    coverage: ImportCoverage
    date_column: str
    columns: Mapping[str, str]
    time_format: str = "24h"
    parser_id: str = "csv_v1"

    def __post_init__(self) -> None:
        if type(self.year) is not int or not 1 <= self.year <= 9999:
            raise ImportValidationError("Enter a valid calendar year")
        if not isinstance(self.timetable, Timetable) or not isinstance(
            self.source_text, str
        ):
            raise ImportValidationError("Invalid import candidate")
        source = self.source_text.encode("utf-8")
        if not source or len(source) > MAX_SOURCE_BYTES:
            raise ImportValidationError(
                "CSV must be nonempty and no larger than 512 KiB"
            )
        if self.sha256 != sha256(source).hexdigest():
            raise ImportValidationError("The stored source checksum does not match")
        self._validate_provenance()
        if any(row.day.year != self.year for row in self.timetable.days):
            raise ImportValidationError("Every date must match the declared year")
        if self.coverage != build_coverage(self.timetable, self.year):
            raise ImportValidationError(
                "The coverage report does not match the timetable"
            )
        warnings = tuple(self.warnings)
        if warnings != coverage_warnings(self.coverage):
            raise ImportValidationError(
                "The warning report does not match the timetable"
            )
        object.__setattr__(self, "warnings", warnings)

    def _validate_provenance(self) -> None:
        if self.parser_id != "csv_v1" or self.time_format not in {"24h", "12h"}:
            raise ImportValidationError("Unsupported parser or time format")
        try:
            header = next(
                csv.reader(
                    io.StringIO(self.source_text.removeprefix("\ufeff"), newline=""),
                    strict=True,
                )
            )
            columns = {
                name: PrayerField(value).value for name, value in self.columns.items()
            }
        except (AttributeError, TypeError, ValueError, StopIteration, csv.Error) as err:
            raise ImportValidationError("Invalid parser provenance") from err
        if (
            not 1 <= len(header) <= 32
            or any(
                not name.strip() or name != name.strip() or len(name) > 256
                for name in header
            )
            or len(set(header)) != len(header)
            or self.date_column not in header
            or self.date_column in columns
            or not columns
            or any(name not in header for name in columns)
            or len(set(columns.values())) != len(columns)
        ):
            raise ImportValidationError(
                "Parser column mapping does not match the source"
            )
        fields = {PrayerField(value) for value in columns.values()}
        if any(
            set(row.original) != set(header)
            or not set(row.times).issubset(fields)
            or row.original[self.date_column].strip() != row.day.isoformat()
            for row in self.timetable.days
        ):
            raise ImportValidationError(
                "Parser column mapping does not match the timetable"
            )
        object.__setattr__(self, "columns", MappingProxyType(columns))

    def as_dict(self) -> dict:
        return {
            "timetable": self.timetable.as_dict(),
            "source_text": self.source_text,
            "sha256": self.sha256,
            "year": self.year,
            "warnings": list(self.warnings),
            "coverage": self.coverage.as_dict(),
            "parser_id": self.parser_id,
            "date_column": self.date_column,
            "columns": dict(self.columns),
            "time_format": self.time_format,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImportCandidate":
        try:
            return cls(
                Timetable.from_dict(data["timetable"]),
                data["source_text"],
                data["sha256"],
                data["year"],
                tuple(data["warnings"]),
                ImportCoverage.from_dict(data["coverage"]),
                date_column=data["date_column"],
                columns=data["columns"],
                time_format=data["time_format"],
                parser_id=data["parser_id"],
            )
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as err:
            raise ImportValidationError("Stored import data is invalid") from err


class TimetableParser(Protocol):
    """Boundary for source parsers; future PDF layouts use the same result."""

    def inspect(self, content: bytes) -> tuple[str, ...]:
        """Return usable source column headers after bounded validation."""
        ...

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
        """Return a validated candidate without promoting it."""
        ...
