"""Versioned setup defaults for explicitly inspected publication editions."""

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Iterable, Mapping

from .import_model import ImportValidationError
from .nms_layout import NMS_COLUMNS
from .nms_monthly_layout import NMS_MONTHLY_COLUMNS
from .zak_annual_layout import ZAK_ANNUAL_COLUMNS
from .zak_ramadan_layout import ZAK_RAMADAN_COLUMNS

if TYPE_CHECKING:
    from .import_model import ImportCandidate


@dataclass(frozen=True)
class PublicationProfile:
    """An immutable edition, not a promise of support for a later publication."""

    profile_id: str
    title: str
    layout_id: str
    kind: str
    year: int
    start_date: date
    end_date: date
    columns: Mapping[str, str]
    time_zone: str = "Europe/London"
    date_column: str = "Date"
    time_format: str = "24h"

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", MappingProxyType(dict(self.columns)))

    @property
    def summary(self) -> str:
        return (
            f"{self.title}. Profile: {self.profile_id}. "
            f"{self.kind.title()} source, year {self.year}; layout {self.layout_id}; "
            f"{self.time_format}, timezone {self.time_zone}. "
            f"Inspected dates: {self.start_date.isoformat()} to {self.end_date.isoformat()}. "
            "Manual PDF upload only; no public HTTPS source has been verified for this profile. "
            "Check the mapping and published values before approval. "
            "Printed Hijri dates never activate Ramadan."
        )

    def validate_dates(self, values: Iterable[date]) -> None:
        expected = tuple(
            self.start_date + timedelta(days=offset)
            for offset in range((self.end_date - self.start_date).days + 1)
        )
        if tuple(values) != expected:
            raise ImportValidationError(
                "The PDF dates do not match the inspected publication edition. "
                "Choose the matching profile, or use the ordinary import route."
            )

    def validate_csv(self, content: str) -> None:
        try:
            records = csv.DictReader(io.StringIO(content))
            self.validate_dates(date.fromisoformat(row["Date"]) for row in records)
        except (KeyError, TypeError, ValueError) as err:
            if isinstance(err, ImportValidationError):
                raise
            raise ImportValidationError(
                "The publication profile needs dated PDF rows"
            ) from err

    def validate_candidate(self, candidate: "ImportCandidate") -> None:
        if (
            candidate.year != self.year
            or candidate.timetable.kind != self.kind
            or candidate.parser_id != self.layout_id
            or candidate.source_format != "pdf"
            or candidate.source_url is not None
            or candidate.date_column != self.date_column
            or candidate.time_format != self.time_format
            or any(
                self.columns.get(name) != field
                for name, field in candidate.columns.items()
            )
        ):
            raise ImportValidationError(
                "The import does not match its publication profile"
            )
        self.validate_dates(row.day for row in candidate.timetable.days)


PROFILES = MappingProxyType(
    {
        profile.profile_id: profile
        for profile in (
            PublicationProfile(
                "nms_annual_2026_v1",
                "Nuneaton Muslim Society — annual calendar 2026",
                "nms_annual_v1",
                "annual",
                2026,
                date(2026, 1, 1),
                date(2026, 12, 31),
                NMS_COLUMNS,
            ),
            PublicationProfile(
                "nms_monthly_may_june_2022_v1",
                "Nuneaton Muslim Society — May–June 2022",
                "nms_monthly_v1",
                "annual",
                2022,
                date(2022, 5, 1),
                date(2022, 6, 30),
                NMS_MONTHLY_COLUMNS,
            ),
            PublicationProfile(
                "zak_annual_2026_v1",
                "Zakariyya Masjid — annual calendar 2026",
                "zak_annual_v1",
                "annual",
                2026,
                date(2026, 1, 1),
                date(2026, 12, 31),
                ZAK_ANNUAL_COLUMNS,
            ),
            PublicationProfile(
                "zak_ramadan_2026_v1",
                "Zakariyya Masjid — separate Ramadan page 2026",
                "zak_ramadan_v1",
                "ramadan",
                2026,
                date(2026, 2, 18),
                date(2026, 3, 20),
                ZAK_RAMADAN_COLUMNS,
            ),
        )
    }
)


def publication_profile(profile_id: str) -> PublicationProfile:
    if not isinstance(profile_id, str) or profile_id not in PROFILES:
        raise ImportValidationError("Choose an inspected publication profile")
    return PROFILES[profile_id]
