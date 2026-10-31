"""Published-value comparisons, complete pagination and safe provenance output."""

import csv
import io
from dataclasses import FrozenInstanceError, replace
from datetime import date, time, timedelta

import pytest

from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.imports.import_comparison import (
    DEFAULT_PAGE_SIZE,
    DIFF_PAGE_SIZE,
    DateChange,
    FieldChange,
    OriginalChange,
    compare_import,
    compare_timetables,
    comparison_overview,
    render_comparison_page,
)
from custom_components.salah_timetable.parsers.csv_parser import CsvParser


def source(
    rows=(("2026-01-01", "05:30", "06:00", "13:00;14:00", "published"),),
    *,
    year=2026,
    kind="annual",
    source_id=None,
    time_format="24h",
    line_ending="\n",
    fajr_column="Fajr",
):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator=line_ending)
    writer.writerow(("Date", fajr_column, "Jamaat", "Jumuah", "Note"))
    writer.writerows(rows)
    return CsvParser().parse(
        output.getvalue().encode(),
        timetable_id=source_id or f"{kind}-{year}",
        kind=kind,
        year=year,
        date_column="Date",
        columns={
            fajr_column: "fajr_begin",
            "Jamaat": "fajr_jamaat",
            "Jumuah": "jumuah",
        },
        time_format=time_format,
    )


def test_first_import_counts_each_date_and_field_and_keeps_original_tokens():
    candidate = source()
    before = candidate.as_dict()
    result = compare_import(candidate, None)
    assert result.previous is None
    assert result.added_dates == (date(2026, 1, 1),)
    assert result.removed_dates == ()
    assert (result.added_fields, result.removed_fields, result.changed_fields) == (
        3,
        0,
        0,
    )
    assert len(result.changes) == 3
    jumuah = next(item for item in result.changes if item.field == PrayerField.JUMUAH)
    assert jumuah.before == ()
    assert jumuah.after == (time(13), time(14))
    assert jumuah.after_tokens[0].value == "13:00;14:00"
    text = render_comparison_page(result)
    assert "First import for this source ID" in text
    assert "Dates added: **1**" in text
    assert "Field entries added: **3**" in text
    assert "absent → 13:00, 14:00" in text
    assert candidate.as_dict() == before
    with pytest.raises(FrozenInstanceError):
        jumuah.before = (time(12),)


def test_identical_import_has_one_page_and_no_changed_values_or_cells():
    candidate = source()
    result = compare_import(candidate, candidate.timetable, candidate)
    assert result.canonical_equal
    assert result.provenance_changed is False
    assert (
        result.changes
        == result.source_changes
        == result.added_dates
        == result.removed_dates
        == ()
    )
    assert result.page_count() == 1
    text = render_comparison_page(result)
    assert "Canonical prayer values and dates are unchanged." in text
    assert "No dated value or original-cell changes to display." in text


def test_canonical_projection_and_original_cell_review_share_published_values():
    previous = source(
        (
            ("2026-01-01", "05:30", "06:00", "13:00;14:00", "old note"),
            ("2026-01-02", "05:31", "06:00", "", "removed note"),
        )
    )
    candidate = source(
        (
            ("2026-01-01", "05:35", "", "13:00", "new note"),
            ("2026-01-03", "05:32", "06:05", "", "added note"),
        )
    )
    full = compare_import(candidate, previous.timetable, previous)
    canonical = compare_timetables(candidate.timetable, previous.timetable)
    shared_dates = {row.day for row in candidate.timetable.days} & {
        row.day for row in previous.timetable.days
    }
    assert {
        (
            change.day,
            change.field,
            tuple(value.strftime("%H:%M") for value in change.before),
            tuple(value.strftime("%H:%M") for value in change.after),
        )
        for change in full.changes
        if change.day in shared_dates
    } == {
        (change.day, change.field, change.before, change.after)
        for change in canonical.changes
        if change.field is not None
    }
    assert len(full.added_dates) == canonical.added_dates == 1
    assert len(full.removed_dates) == canonical.removed_dates == 1
    assert full.changed_fields == canonical.changed_fields == 2
    # The canonical API groups a date into one entry; detailed review exposes
    # its fields and every original cell separately, preserving both contracts.
    assert full.added_fields == 2 and canonical.added_fields == 0
    assert full.removed_fields == 3 and canonical.removed_fields == 1
    assert DEFAULT_PAGE_SIZE == 10 and DIFF_PAGE_SIZE == 20
    filtered = "\n".join(
        render_comparison_page(full, page, canonical_only=True)
        for page in range(full.page_count(canonical_only=True))
    )
    assert "date added" in filtered and "date removed" in filtered
    assert "fajr begin" in filtered
    assert "original cell Note" not in filtered
    assert "Original-cell-only changes are hidden" in filtered


def test_comparison_overview_summarizes_provenance_without_copying_dated_entries():
    previous = source()
    candidate = source((("2026-01-01", "05:35", "06:00", "13:00", "new note"),))
    comparison = compare_import(candidate, previous.timetable, previous)
    overview = comparison_overview(comparison)
    assert "Field entries changed: **2**" in overview
    assert "Additional original-cell changes: **1**" in overview
    assert f"SHA-256: `{candidate.sha256}`" in overview
    assert f"SHA-256: `{previous.sha256}`" in overview
    assert "new note" not in overview
    assert "- 2026-01-01 —" not in overview
    assert "page 1 of" not in overview
    assert overview in render_comparison_page(comparison)


def test_whole_source_replacement_exposes_removed_dates_fields_and_jumuah_slots():
    previous = source(
        (
            ("2026-01-01", "05:30", "06:00", "13:00;14:00", "first"),
            ("2026-01-02", "05:31", "06:00", "", "second"),
        )
    )
    candidate = source(
        (
            ("2026-01-01", "05:35", "", "13:00", "updated"),
            ("2026-01-03", "05:32", "06:05", "", "third"),
        )
    )
    result = compare_import(candidate, previous.timetable, previous)
    assert result.added_dates == (date(2026, 1, 3),)
    assert result.removed_dates == (date(2026, 1, 2),)
    assert (result.added_fields, result.removed_fields, result.changed_fields) == (
        2,
        3,
        2,
    )
    jumuah = next(item for item in result.changes if item.field == PrayerField.JUMUAH)
    assert jumuah.before == (time(13), time(14))
    assert jumuah.after == (time(13),)
    text = "\n".join(
        render_comparison_page(result, page) for page in range(result.page_count())
    )
    assert "05:30 → 05:35" in text
    assert "13:00, 14:00 → 13:00" in text
    assert "06:00 → absent" in text
    assert "2026-01-02 — date removed" in text
    assert "whole-source" in text.lower()
    assert "exclude effective Ramadan merging" in text


def test_ditto_and_explicit_time_are_original_cell_changes_only():
    rows = (
        ("2026-01-01", "05:30", "06:00", "", "same"),
        ("2026-01-02", "05:31", '"', "", "same"),
    )
    previous = source(rows)
    candidate = source((rows[0], ("2026-01-02", "05:31", "06:00", "", "same")))
    result = compare_import(candidate, previous.timetable, previous)
    assert result.canonical_equal
    assert result.changes == ()
    assert len(result.source_changes) == 1
    assert result.source_changes[0].before == '"'
    assert result.source_changes[0].after == "06:00"
    text = render_comparison_page(result)
    assert "original cell Jamaat" in text
    assert "&quot;" in text
    assert "Canonical prayer values and dates are unchanged." in text


def test_12_hour_tokens_normalize_to_the_same_values_but_remain_inspectable():
    previous = source()
    candidate = source(
        (("2026-01-01", "05:30 AM", "06:00 AM", "01:00 PM;02:00 PM", "published"),),
        time_format="12h",
    )
    result = compare_import(candidate, previous.timetable, previous)
    assert result.canonical_equal
    assert result.changed_fields == 0
    assert result.provenance_changed
    assert len(result.source_changes) == 3
    text = render_comparison_page(result)
    assert "05:30 AM" in text and "05:30" in text
    assert "Source bytes or provenance metadata changed." in text


def test_different_file_bytes_do_not_imply_changed_prayers_or_tokens():
    previous, candidate = source(), source(line_ending="\r\n")
    assert previous.sha256 != candidate.sha256
    result = compare_import(candidate, previous.timetable, previous)
    assert result.canonical_equal and result.provenance_changed
    assert not result.changes and not result.source_changes
    text = render_comparison_page(result)
    assert "different file checksum alone does not mean prayer values changed" in text


def test_location_only_changes_are_identified_without_exposing_private_urls():
    previous = replace(
        source(), source_url="https://old.example.org/private?token=old-secret"
    )
    candidate = replace(
        previous, source_url="https://new.example.org/private?token=new-secret"
    )
    result = compare_import(candidate, previous.timetable, previous)
    assert result.provenance_changed and result.canonical_equal
    text = render_comparison_page(result)
    assert "Source location changed; URLs are omitted." in text
    assert "old-secret" not in text and "new-secret" not in text
    assert "example.org" not in text and "https:" not in text


def test_transport_validators_are_not_published_value_or_provenance_changes():
    previous = source()
    candidate = replace(previous, etag='"private-etag"', last_modified="private-header")
    result = compare_import(candidate, previous.timetable, previous)
    assert result.provenance_changed is False
    text = render_comparison_page(result)
    assert "private-etag" not in text and "private-header" not in text


def test_renamed_mapping_and_date_columns_are_visible_in_metadata():
    previous = source()
    content = previous.source_text.replace("Date,Fajr,", "Printed Date,Dawn,").encode()
    candidate = CsvParser().parse(
        content,
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Printed Date",
        columns={"Dawn": "fajr_begin", "Jamaat": "fajr_jamaat", "Jumuah": "jumuah"},
    )
    result = compare_import(candidate, previous.timetable, previous)
    assert result.canonical_equal and result.provenance_changed
    text = render_comparison_page(result)
    assert "Date column: Date." in text
    assert "Date column: Printed Date." in text
    assert "Fajr → fajr\\_begin" in text and "Dawn → fajr\\_begin" in text


def test_legacy_multi_year_target_keeps_all_removed_dates_in_scope():
    candidate = source()
    legacy = Timetable(
        candidate.timetable.timetable_id,
        "annual",
        (
            DailyPrayers(
                date(2025, 12, 31),
                {PrayerField.FAJR_BEGIN: (time(0),)},
                {"Old": "00:00"},
            ),
            *candidate.timetable.days,
        ),
    )
    result = compare_import(candidate, legacy)
    assert result.removed_dates == (date(2025, 12, 31),)
    assert result.removed_fields == 1
    text = render_comparison_page(result)
    assert "Annual 2025–2026" in text
    assert "00:00 → absent" in text
    assert "Previous source provenance is unavailable" in text
    assert "original column mapping unavailable" in text


def test_legacy_empty_date_rows_are_paginated_even_without_field_changes():
    candidate = source()
    legacy = Timetable(
        candidate.timetable.timetable_id,
        "annual",
        (*candidate.timetable.days, DailyPrayers(date(2026, 1, 2), {}, {})),
    )
    result = compare_import(candidate, legacy)
    assert result.removed_dates == (date(2026, 1, 2),)
    assert result.changes == ()
    assert result.items == (DateChange(date(2026, 1, 2), False),)
    assert "2026-01-02 — date removed" in render_comparison_page(result)


def test_new_and_removed_dates_retain_unmapped_legacy_notes_and_blank_cells():
    candidate = source((("2026-01-02", "05:35", "06:05", "", "new note"),))
    previous = Timetable(
        "annual-2026",
        "annual",
        (
            DailyPrayers(
                date(2026, 1, 1),
                {PrayerField.FAJR_BEGIN: (time(5, 30),)},
                {
                    "Legacy date": "2026-01-01",
                    "Unknown original": "old token",
                    "Blank": "",
                },
            ),
        ),
    )
    result = compare_import(candidate, previous)
    changes = {
        (item.day, item.column): (item.before, item.after)
        for item in result.source_changes
    }
    assert changes[(date(2026, 1, 1), "Unknown original")] == ("old token", None)
    assert changes[(date(2026, 1, 1), "Blank")] == ("", None)
    assert changes[(date(2026, 1, 2), "Note")] == (None, "new note")
    assert changes[(date(2026, 1, 2), "Jumuah")] == (None, "")
    # Mapped, displayed source cells do not get a duplicate original-cell entry.
    assert (date(2026, 1, 2), "Fajr") not in changes
    assert (date(2026, 1, 2), "Jamaat") not in changes
    pages = [
        render_comparison_page(result, page, page_size=2)
        for page in range(result.page_count(2))
    ]
    text = "\n".join(pages)
    assert "original cell Unknown original: “old token” → absent" in text
    assert "original cell Blank: “” → absent" in text
    assert "original cell Note: absent → “new note”" in text
    assert "original cell Jumuah: absent → “”" in text
    assert "Comparison entries 9–10 of 11" in text


def test_first_import_pagination_exposes_notes_and_blank_cells_on_every_date():
    start = date(2028, 1, 1)
    rows = tuple(
        ((start + timedelta(days=day)).isoformat(), "05:30", "06:00", "", f"note {day}")
        for day in range(32)
    )
    result = compare_import(source(rows, year=2028), None)
    assert len(result.changes) == 64
    assert len(result.source_changes) == 96  # Original date, blank Jumuah and note.
    assert len(result.items) == 192
    assert result.page_count() == 20
    text = "\n".join(
        render_comparison_page(result, page) for page in range(result.page_count())
    )
    for day in range(32):
        dated = (start + timedelta(days=day)).isoformat()
        assert text.count(f"- {dated} — original cell Note: absent → “note {day}”") == 1
        assert text.count(f"- {dated} — original cell Jumuah: absent → “”") == 1
        assert text.count(f"- {dated} — fajr begin: **absent → 05:30**") == 1


@pytest.mark.parametrize(
    "mismatch", ["id", "kind", "metadata", "metadata_without_table"]
)
def test_other_source_identities_cannot_be_silently_compared(mismatch):
    candidate = source()
    previous = candidate.timetable
    provenance = candidate
    if mismatch == "id":
        previous = replace(previous, timetable_id="another-source")
        provenance = None
    elif mismatch == "kind":
        previous = replace(previous, kind="ramadan")
        provenance = None
    elif mismatch == "metadata":
        provenance = source(
            (("2026-01-01", "05:40", "06:00", "13:00;14:00", "changed"),)
        )
    else:
        previous = None
    with pytest.raises(ValueError):
        compare_import(candidate, previous, provenance)


def test_source_labels_cells_and_annotations_are_escaped_and_bounded():
    label = "[Fajr](javascript:alert) <b>bold</b> #header"
    previous = source(fajr_column=label)
    candidate = source(
        (
            (
                "2026-01-01",
                "05:35",
                "06:00",
                "13:00;14:00",
                "*note* <script>x</script> https://private.example.org/?key=secret",
            ),
        ),
        fajr_column=label,
    )
    result = compare_import(candidate, previous.timetable, previous)
    text = render_comparison_page(result)
    assert "<b>" not in text and "<script>" not in text
    assert "[Fajr](javascript:alert)" not in text
    assert "\\[Fajr\\]" in text and "&lt;b&gt;" in text
    assert "\\*note\\*" in text
    assert "private.example.org" not in text and "key=secret" not in text
    assert "URL omitted" in text
    long_note = "*" * 250
    long = source((("2026-01-01", "05:30", "06:00", "13:00;14:00", long_note),))
    text = render_comparison_page(compare_import(long, previous.timetable, previous))
    assert "truncated; inspect retained source" in text
    assert long_note not in text


def test_leap_year_pagination_reaches_every_change_once_with_complete_counts():
    start = date(2028, 1, 1)
    old_rows = tuple(
        ((start + timedelta(days=day)).isoformat(), "05:30", "06:00", "", "old")
        for day in range(366)
    )
    new_rows = tuple((row[0], "05:35", row[2], row[3], "new") for row in old_rows)
    previous, candidate = source(old_rows, year=2028), source(new_rows, year=2028)
    result = compare_import(candidate, previous.timetable, previous)
    assert result.changed_fields == 366
    assert len(result.source_changes) == 366
    assert result.page_count() == 74
    assert result.page_count(7) == 105
    pages = [
        render_comparison_page(result, page) for page in range(result.page_count())
    ]
    assert all("Field entries changed: **366**" in page for page in pages)
    all_text = "\n".join(pages)
    for day in range(366):
        dated = (start + timedelta(days=day)).isoformat()
        assert all_text.count(f"- {dated} — fajr begin: **05:30 → 05:35**") == 1
        assert all_text.count(f"- {dated} — original cell Note:") == 1
    assert "2028-02-29 — fajr begin" in all_text
    assert "2028-12-31 — original cell Note:" in pages[-1]
    assert all(len(page) < 10000 for page in pages)
    assert len({(item.day, type(item)) for item in result.items}) == 732


def test_ramadan_comparison_remains_raw_source_values_without_effective_fallback():
    previous = source(kind="ramadan")
    candidate = source(
        (("2026-01-01", "05:35", "", "", "partial override"),), kind="ramadan"
    )
    result = compare_import(candidate, previous.timetable, previous)
    assert result.removed_fields == 2
    assert result.changed_fields == 1
    assert all(
        isinstance(item, (DateChange, FieldChange, OriginalChange))
        for item in result.items
    )
    text = render_comparison_page(result)
    assert "Ramadan 2026" in text
    assert "06:00 → absent" in text
    assert "13:00, 14:00 → absent" in text
    assert "After Isha" not in text


@pytest.mark.parametrize("page", [-1, 1, True, 1.5, "0"])
def test_invalid_page_numbers_are_rejected(page):
    candidate = source()
    result = compare_import(candidate, candidate.timetable, candidate)
    with pytest.raises(ValueError, match="page is outside"):
        render_comparison_page(result, page)


@pytest.mark.parametrize("page_size", [0, -1, 101, True, "10", 1.5])
def test_invalid_page_sizes_are_rejected(page_size):
    candidate = source()
    result = compare_import(candidate, None)
    with pytest.raises(ValueError, match="page size"):
        render_comparison_page(result, 0, page_size)
    with pytest.raises(ValueError, match="page size"):
        result.page_count(page_size)
