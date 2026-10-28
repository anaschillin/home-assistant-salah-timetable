"""Ramadan review distinguishes source omissions from effective exact-date data."""

from datetime import date, time, timedelta

import pytest

from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.ramadan import RamadanSettings
from custom_components.salah_timetable.ramadan_validation import (
    ramadan_review,
    validate_ramadan_selection,
)

DAY = date(2028, 2, 29)


def row(day=DAY, **values):
    return DailyPrayers(
        day,
        {
            PrayerField(field): (time.fromisoformat(value),)
            for field, value in values.items()
        },
        values,
    )


def table(*rows, kind="ramadan", source_id="ramadan-2028"):
    return Timetable(source_id, kind, tuple(rows))


def confirmed(start=DAY, end=DAY, **values):
    return RamadanSettings(confirmed_start=start, confirmed_end=end, **values)


def test_sparse_source_reports_missing_confirmed_edges_and_annual_fallback():
    start, end = DAY - timedelta(days=1), DAY + timedelta(days=1)
    candidate = table(row(iftar="17:45"))
    annual = table(
        row(start, fajr_begin="05:10"), kind="annual", source_id="annual-2028"
    )
    result = ramadan_review(candidate, (annual,), confirmed(start, end))
    assert "2028-02-28 to 2028-03-01" in result
    assert "all **3 adjusted confirmed dates**" in result
    assert "Dates with an active Ramadan source row: **1** — 2028-02-29" in result
    assert "Dates using annual data without a Ramadan row: **1** — 2028-02-28" in result
    assert "Dates with no effective prayer timestamps: **1** — 2028-03-01" in result


def test_partial_override_retains_annual_fields_and_iftar_default_without_mutation():
    annual = table(
        row(fajr_begin="05:30", fajr_jamaat="06:00", maghrib_begin="17:45"),
        kind="annual",
        source_id="annual-2028",
    )
    previous = table(row(sehri_ends="05:20", taraweeh="20:30"))
    candidate = table(row(sehri_ends="05:15"))
    before = (annual.as_dict(), previous.as_dict(), candidate.as_dict())
    result = ramadan_review(candidate, (annual, previous), confirmed())
    assert "Source omissions: **15 field values**" in result
    assert "fajr_begin: 1, fajr_jamaat: 1, maghrib_begin: 1" in result
    assert "Iftar defaults to effective Maghrib beginning: **1** — 2028-02-29" in result
    assert "Taraweeh is text only: After Isha Jamaat: **1**" in result
    unavailable = result.split("Unavailable timestamps after merging and defaults")[1]
    assert "fajr_begin:" not in unavailable
    assert "iftar:" not in unavailable
    assert "taraweeh: 1" in unavailable
    assert before == (annual.as_dict(), previous.as_dict(), candidate.as_dict())


@pytest.mark.parametrize("source", ["annual", "ramadan"])
def test_published_iftar_is_never_reported_as_default(source):
    annual_values = {"maghrib_begin": "17:45"}
    override_values = {"sehri_ends": "05:15"}
    (annual_values if source == "annual" else override_values)["iftar"] = "17:50"
    annual = table(row(**annual_values), kind="annual", source_id="annual-2028")
    result = ramadan_review(table(row(**override_values)), (annual,), confirmed())
    assert "Iftar defaults to effective Maghrib beginning: **0**" in result


def test_date_adjustment_changes_window_not_source_dates():
    candidate = table(row(iftar="17:45"))
    result = ramadan_review(candidate, (), confirmed(date_adjustment=1))
    assert "2028-03-01 to 2028-03-01" in result
    assert "adjustment +1 days" in result
    assert "Candidate dates outside the saved window: **1** — 2028-02-29" in result
    assert "Dates with an active Ramadan source row: **0**" in result
    assert "Dates with no effective prayer timestamps: **1** — 2028-03-01" in result


def test_unconfirmed_dates_never_activate_source_and_cannot_claim_month_coverage():
    result = ramadan_review(table(row(iftar="17:45")), (), RamadanSettings())
    assert "no confirmed dates" in result
    assert "Full Ramadan coverage cannot be assessed" in result
    assert "Dates with an active Ramadan source row: **0**" in result
    assert "Dates with no effective prayer timestamps: **1**" in result


def test_manual_on_is_persistent_and_reviews_candidate_dates_only():
    candidate = table(row(iftar="17:45"))
    result = ramadan_review(
        candidate,
        (),
        confirmed(DAY + timedelta(days=1), DAY + timedelta(days=1), mode="on"),
    )
    assert "Ramadan stays active until switched off" in result
    assert "saved confirmation dates do not limit manual activation" in result
    assert "candidate's **1 supplied dates** only" in result
    assert "Dates with an active Ramadan source row: **1** — 2028-02-29" in result


def test_off_keeps_annual_data_and_disables_defaults():
    annual = table(row(maghrib_begin="17:45"), kind="annual", source_id="annual-2028")
    result = ramadan_review(table(row(iftar="17:50")), (annual,), confirmed(mode="off"))
    assert "Ramadan overrides are disabled" in result
    assert "Dates with an active Ramadan source row: **0**" in result
    assert "Dates using annual data without a Ramadan row: **1**" in result
    assert "Iftar defaults to effective Maghrib beginning: **0**" in result
    assert "Taraweeh is text only: After Isha Jamaat: **0**" in result


def test_explicit_source_excludes_candidate_without_rendering_its_identity():
    excluded = table(row(iftar="17:45"), source_id="<script>candidate</script>")
    chosen = table(row(sehri_ends="05:15"), source_id="selected")
    result = ramadan_review(excluded, (chosen,), confirmed(source_id="selected"))
    assert "candidate is excluded by the explicitly selected Ramadan source" in result
    assert "Dates with an active Ramadan source row: **1**" in result
    assert "iftar: 1" in result
    assert "<script>" not in result
    assert "selected" not in result.replace("explicitly selected", "")


def test_overlap_is_reported_without_misclassifying_unresolved_as_missing():
    candidate = table(row(iftar="17:45"))
    legacy = table(row(sehri_ends="05:15"), source_id="legacy")
    result = ramadan_review(candidate, (legacy,), confirmed())
    assert "Cannot resolve overlapping or inconsistent sources" in result
    assert "Unresolved dates: **1** — 2028-02-29" in result
    assert "Dates with no effective prayer timestamps: **0**" in result
    assert (
        "Unavailable timestamps after merging and defaults (number of reviewed dates): none"
        in result
    )


def test_time_conflicts_are_advisory_and_include_cross_source_effective_values():
    annual = table(
        row(fajr_begin="05:30", maghrib_begin="17:45"),
        kind="annual",
        source_id="annual-2028",
    )
    candidate = table(row(fajr_jamaat="04:30", sehri_ends="12:00", iftar="04:00"))
    result = ramadan_review(candidate, (annual,), confirmed())
    assert "Fajr Jamaat before beginning: **1** — 2028-02-29" in result
    assert "Sehri ends after Fajr beginning: **1** — 2028-02-29" in result
    assert "Iftar before Maghrib beginning: **1** — 2028-02-29" in result
    assert "do not change times or block approval" in result
    assert candidate.days[0].times[PrayerField.FAJR_JAMAAT] == (time(4, 30),)


def test_equal_times_and_missing_comparison_fields_do_not_warn():
    candidate = table(
        row(fajr_begin="05:30", fajr_jamaat="05:30", sehri_ends="05:30", iftar="17:45")
    )
    result = ramadan_review(candidate, (), confirmed())
    assert "time-order warnings" not in result


@pytest.mark.parametrize(
    "settings",
    [RamadanSettings(), confirmed(mode="off"), confirmed(source_id="another-source")],
)
def test_source_time_conflicts_are_reported_even_when_candidate_is_inactive(settings):
    candidate = table(
        row(
            fajr_begin="05:30",
            fajr_jamaat="04:30",
            sehri_ends="12:00",
            maghrib_begin="17:45",
            iftar="04:00",
        )
    )
    before = candidate.as_dict()
    result = ramadan_review(candidate, (), settings)
    assert "Source time-order warnings" in result
    assert "Fajr Jamaat before beginning: **1** — 2028-02-29" in result
    assert "Sehri ends after Fajr beginning: **1** — 2028-02-29" in result
    assert "Iftar before Maghrib beginning: **1** — 2028-02-29" in result
    assert "Effective time-order warnings" not in result
    assert "Dates with an active Ramadan source row: **0**" in result
    assert candidate.as_dict() == before


def test_output_bounds_date_samples_and_uses_only_fixed_labels():
    rows = tuple(
        row(DAY + timedelta(days=offset), fajr_begin="05:30", fajr_jamaat="04:30")
        for offset in range(30)
    )
    result = ramadan_review(table(*rows), (), confirmed(DAY, rows[-1].day))
    assert "Fajr Jamaat before beginning: **30**" in result
    assert "(+25 more)" in result
    assert len(result) < 5500


@pytest.mark.parametrize("mode", ["auto", "on"])
def test_selection_rejects_active_overlapping_rows(mode):
    tables = (table(row(iftar="17:45")), table(row(iftar="17:50"), source_id="legacy"))
    with pytest.raises(ValueError, match="active Ramadan timetables overlap"):
        validate_ramadan_selection(tables, confirmed(mode=mode))


@pytest.mark.parametrize(
    "settings",
    [
        RamadanSettings(),
        confirmed(mode="off"),
        confirmed(source_id="ramadan-2028"),
        confirmed(source_id="missing"),
        confirmed(date_adjustment=1),
    ],
)
def test_selection_ignores_inactive_and_excluded_rows(settings):
    tables = (table(row(iftar="17:45")), table(row(iftar="17:50"), source_id="legacy"))
    validate_ramadan_selection(tables, settings)


def test_selection_handles_leap_and_year_boundaries_without_guessing():
    leap_tables = (
        table(row(DAY, iftar="17:45")),
        table(row(DAY + timedelta(days=1), iftar="17:50"), source_id="next"),
    )
    validate_ramadan_selection(leap_tables, confirmed(DAY, DAY + timedelta(days=1)))
    last = date(2030, 12, 31)
    next_day = date(2031, 1, 1)
    year_tables = (
        table(row(last, iftar="16:30"), source_id="ramadan-2030"),
        table(row(next_day, iftar="16:31"), source_id="ramadan-2031"),
    )
    validate_ramadan_selection(year_tables, confirmed(last, next_day))
    result = ramadan_review(
        year_tables[1], (year_tables[0],), confirmed(last, next_day)
    )
    assert (
        "Dates with an active Ramadan source row: **2** — 2030-12-31, 2031-01-01"
        in result
    )


def test_selection_ignores_annual_overlap_because_storage_validates_that_separately():
    tables = (
        table(row(iftar="17:45"), kind="annual", source_id="annual-a"),
        table(row(iftar="17:50"), kind="annual", source_id="annual-b"),
    )
    validate_ramadan_selection(tables, confirmed())
