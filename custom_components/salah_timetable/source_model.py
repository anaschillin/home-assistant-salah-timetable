"""Validated remote source profiles and redacted check metadata."""

import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from .import_model import ImportValidationError
from .model import PrayerField

PDF_PARSER_IDS = frozenset(
    {
        "pdf_table_v1",
        "nms_annual_v1",
        "nms_monthly_v1",
        "zak_ramadan_v1",
        "zak_annual_v1",
    }
)
CHECK_STATUSES = frozenset(
    {
        "configured",
        "checking",
        "unchanged",
        "pending",
        "updated",
        "approved",
        "rejected",
        "error",
        "disabled",
    }
)
CHECK_FIELDS = frozenset(
    {
        "status",
        "last_checked",
        "last_success",
        "last_seen_sha256",
        "etag",
        "last_modified",
        "error_code",
    }
)


def validate_source_url(value: str) -> str:
    """Use the downloader's canonical structural policy without resolving DNS."""
    from .download import validate_url

    if not isinstance(value, str) or len(value) > 2048:
        raise ImportValidationError("Invalid timetable source URL")
    return str(validate_url(value))


def validate_validator(value: str | None) -> str | None:
    """HTTP validators are metadata, never arbitrary headers or log messages."""
    if value is not None and (
        not isinstance(value, str)
        or len(value) > 512
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ImportValidationError("Invalid HTTP validator")
    return value


@dataclass(frozen=True)
class RemoteSource:
    """One explicit, reproducible URL/parser configuration for a source."""

    source_id: str
    url: str
    media_type: str
    kind: str
    year: int
    date_column: str
    columns: Mapping[str, str]
    time_format: str = "24h"
    parser_id: str = "pdf_table_v1"

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", self.source_id
        ):
            raise ImportValidationError("Invalid timetable source identity")
        object.__setattr__(self, "url", validate_source_url(self.url))
        if self.media_type not in {"csv", "pdf"} or self.kind not in {
            "annual",
            "ramadan",
        }:
            raise ImportValidationError("Invalid timetable source type")
        if type(self.year) is not int or not 1 <= self.year <= 9999:
            raise ImportValidationError("Invalid timetable source year")
        if (
            self.time_format not in {"24h", "12h"}
            or (self.media_type == "csv" and self.parser_id != "csv_v1")
            or (self.media_type == "pdf" and self.parser_id not in PDF_PARSER_IDS)
        ):
            raise ImportValidationError("Unsupported timetable source parser")
        if (
            not isinstance(self.date_column, str)
            or not self.date_column.strip()
            or len(self.date_column) > 256
        ):
            raise ImportValidationError("Invalid source date column")
        try:
            columns = {
                name: PrayerField(field).value for name, field in self.columns.items()
            }
        except (AttributeError, TypeError, ValueError) as err:
            raise ImportValidationError("Invalid source column mapping") from err
        if (
            not 1 <= len(columns) <= 16
            or len(set(columns.values())) != len(columns)
            or self.date_column in columns
            or any(
                not isinstance(name, str) or not name.strip() or len(name) > 256
                for name in columns
            )
        ):
            raise ImportValidationError("Invalid source column mapping")
        object.__setattr__(self, "columns", MappingProxyType(columns))

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "media_type": self.media_type,
            "kind": self.kind,
            "year": self.year,
            "date_column": self.date_column,
            "columns": dict(self.columns),
            "time_format": self.time_format,
            "parser_id": self.parser_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RemoteSource":
        try:
            return cls(
                data["source_id"],
                data["url"],
                data["media_type"],
                data["kind"],
                data["year"],
                data["date_column"],
                data["columns"],
                data["time_format"],
                data["parser_id"],
            )
        except (AttributeError, KeyError, TypeError, ValueError) as err:
            raise ImportValidationError("Stored remote source is invalid") from err


def validate_check(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate only safe bounded status codes, timestamps and HTTP validators."""
    if not isinstance(data, Mapping) or set(data) - CHECK_FIELDS:
        raise ImportValidationError("Invalid source check metadata")
    result = dict(data)
    if "status" in result and result["status"] not in CHECK_STATUSES:
        raise ImportValidationError("Invalid source check status")
    for key in ("last_checked", "last_success"):
        value = result.get(key)
        if value is not None:
            if not isinstance(value, str) or len(value) > 40:
                raise ImportValidationError("Invalid source check timestamp")
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as err:
                raise ImportValidationError("Invalid source check timestamp") from err
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ImportValidationError(
                    "Source check timestamp must have a timezone"
                )
    digest = result.get("last_seen_sha256")
    if digest is not None and (
        not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
    ):
        raise ImportValidationError("Invalid source check digest")
    for key in ("etag", "last_modified"):
        if key in result:
            validate_validator(result[key])
    code = result.get("error_code")
    if code is not None and (
        not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code)
    ):
        raise ImportValidationError("Invalid source check error code")
    return MappingProxyType(result)
