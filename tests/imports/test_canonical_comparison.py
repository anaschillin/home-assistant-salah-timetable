"""Milestone 17 compares exact published source values, never effective fallbacks."""

from datetime import date, time

import pytest

from custom_components.salah_timetable.imports.import_comparison import (
    DIFF_PAGE_SIZE,
    compare_timetables,
    diff_overview,
    render_diff_page,
)
from custom_components.salah_timetable.domain.model import DailyPrayers, PrayerField, Timetable

F = PrayerField


def row(day, **fields):
    return DailyPrayers(
        date.fromisoformat(day),
        {
            F(key): tuple(time.fromisoformat(value) for value in values)
            for key, values in fields.items()
        },
        {"Source label": "original-only string"},
    )


def table(*rows, kind="annual", identifier="annual-2026"):
    return Timetable(identifier, kind, rows)


def test_diff_tracks_added_and_removed_dates_and_changed_and_missing_fields():
    approved = table(
        row("2026-01-01", fajr_begin=("05:00",), jumuah=("13:00", "14:00")),
        row("2026-01-02", fajr_begin=("05:10",), isha_begin=("20:00",)),
        row("2026-01-03", fajr_begin=("05:15",)),
    )
    proposal = table(
        row(
            "2026-01-01",
            fajr_begin=("05:05",),
            jumuah=("13:00", "13:30", "14:00"),
            isha_begin=("20:00",),
        ),
        row("2026-01-02", fajr_begin=("05:10",)),
        row("2026-01-04", fajr_begin=("05:20",)),
    )
    diff = compare_timetables(proposal, approved)
    assert (
        diff.added_dates,
        diff.removed_dates,
        diff.changed_fields,
        diff.added_fields,
        diff.removed_fields,
    ) == (1, 1, 2, 1, 1)
    assert [change.kind for change in diff.changes] == [
        "field_changed",
        "field_added",
        "field_changed",
        "field_removed",
        "date_removed",
        "date_added",
    ]
    description = render_diff_page(diff, 0)
    assert "13:00, 14:00 → 13:00, 13:30, 14:00" in description
    assert "isha_begin: absent → 20:00" in description
    assert "2026-01-03 (date removed)" in description
    assert "2026-01-04 (date added)" in description
    assert "original-only string" not in description


def test_first_import_and_format_only_same_canonical_values():
    first = table(row("2026-02-01", fajr_begin=("05:00",)))
    diff = compare_timetables(first, None)
    assert not diff.previous_exists
    assert diff.added_dates == 1
    assert "no existing approved version" in diff_overview(diff)
    restored_with_other_source_text = Timetable(
        first.timetable_id,
        first.kind,
        (DailyPrayers(first.days[0].day, first.days[0].times, {"date": "other"}),),
    )
    identical = compare_timetables(restored_with_other_source_text, first)
    assert identical.changes == ()
    assert identical.page_count == 1
    assert "original tokens or provenance may still differ" in diff_overview(identical)
    assert "No canonical date or field changes" in render_diff_page(identical, 0)


def test_compares_only_exact_source_identity_without_cross_year_or_kind():
    first = table(row("2026-02-01", fajr_begin=("05:00",)))
    for other in (
        table(row("2026-02-01", fajr_begin=("05:00",)), identifier="annual-2027"),
        table(
            row("2026-02-01", fajr_begin=("05:00",)),
            identifier="annual-2026",
            kind="ramadan",
        ),
    ):
        with pytest.raises(ValueError, match="different timetable source"):
            compare_timetables(other, first)


def test_diff_paging_uses_stable_date_order_and_rejects_bad_pages():
    items = tuple(
        row(f"2026-03-{day:02d}", fajr_begin=("05:00",))
        for day in range(1, DIFF_PAGE_SIZE + 4)
    )
    diff = compare_timetables(table(*reversed(items)), None)
    assert diff.page_count == 2
    assert len(diff.changes) == DIFF_PAGE_SIZE + 3
    assert "2026-03-01" in render_diff_page(diff, 0)
    assert "2026-03-20" in render_diff_page(diff, 0)
    assert "2026-03-21" not in render_diff_page(diff, 0)
    assert "2026-03-21" in render_diff_page(diff, 1)
    assert "2026-03-23" in render_diff_page(diff, 1)
    with pytest.raises(ValueError, match="Invalid comparison page"):
        render_diff_page(diff, 2)


def test_effective_ramadan_fallback_does_not_create_or_fill_published_values():
    approved = table(
        row("2026-03-01", maghrib_begin=("18:05",)),
        kind="ramadan",
        identifier="ramadan-2026",
    )
    incoming = table(
        row("2026-03-01", maghrib_begin=("18:05",), iftar=("18:06",)),
        kind="ramadan",
        identifier="ramadan-2026",
    )
    diff = compare_timetables(incoming, approved)
    assert diff.added_fields == 1
    assert [c.field for c in diff.changes] == [F.IFTAR]
    assert "iftar: absent → 18:06" in render_diff_page(diff, 0)
