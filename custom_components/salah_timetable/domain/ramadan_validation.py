"""Review exact Ramadan coverage without changing published prayer values."""

from collections import Counter
from datetime import date, timedelta

from .model import DailyPrayers, PrayerField, Timetable
from .ramadan import RamadanSettings, resolve_day

_SAMPLE_DATES = 5
_ORDER_CHECKS = (
    (PrayerField.FAJR_JAMAAT, PrayerField.FAJR_BEGIN, "Fajr Jamaat before beginning"),
    (
        PrayerField.DHUHR_JAMAAT,
        PrayerField.DHUHR_BEGIN,
        "Dhuhr Jamaat before beginning",
    ),
    (PrayerField.ASR_JAMAAT, PrayerField.ASR_BEGIN, "Asr Jamaat before beginning"),
    (
        PrayerField.MAGHRIB_JAMAAT,
        PrayerField.MAGHRIB_BEGIN,
        "Maghrib Jamaat before beginning",
    ),
    (PrayerField.ISHA_JAMAAT, PrayerField.ISHA_BEGIN, "Isha Jamaat before beginning"),
    (PrayerField.IFTAR, PrayerField.MAGHRIB_BEGIN, "Iftar before Maghrib beginning"),
    (PrayerField.FAJR_BEGIN, PrayerField.SEHRI_ENDS, "Sehri ends after Fajr beginning"),
)


def validate_ramadan_selection(
    timetables: tuple[Timetable, ...], settings: RamadanSettings
) -> None:
    """Reject competing selected rows only on explicitly active dates."""
    seen = set()
    for table in timetables:
        if table.kind != "ramadan" or (
            settings.source_id is not None and table.timetable_id != settings.source_id
        ):
            continue
        for row in table.days:
            if not settings.is_active(row.day):
                continue
            if row.day in seen:
                raise ValueError(
                    "Select a Ramadan source because active Ramadan timetables overlap"
                )
            seen.add(row.day)


def _samples(days: list[date] | tuple[date, ...]) -> str:
    shown = ", ".join(day.isoformat() for day in days[:_SAMPLE_DATES])
    extra = len(days) - _SAMPLE_DATES
    return shown + (f" (+{extra} more)" if extra > 0 else "")


def _date_count(label: str, days: list[date] | tuple[date, ...]) -> str:
    return f"{label}: **{len(days)}**" + (f" — {_samples(days)}" if days else "")


def _field_counts(counts: Counter) -> str:
    return (
        ", ".join(
            f"{field.value}: {counts[field]}" for field in PrayerField if counts[field]
        )
        or "none"
    )


def _time_warnings(row: DailyPrayers) -> tuple[str, ...]:
    return tuple(
        label
        for earlier, later, label in _ORDER_CHECKS
        if earlier in row.times
        and later in row.times
        and row.times[earlier][0] < row.times[later][0]
    )


def _warning_lines(conflicts: dict[str, list[date]], label: str) -> list[str]:
    if not any(conflicts.values()):
        return []
    return [
        f"**{label}: check the published values. "
        "These warnings do not change times or block approval.** "
        "Checks compare local times on the same Gregorian date.",
        *(_date_count(warning, days) for warning, days in conflicts.items() if days),
    ]


def ramadan_review(
    table: Timetable,
    existing: tuple[Timetable, ...],
    settings: RamadanSettings,
) -> str:
    """Describe the replacement's effective coverage with bounded, safe samples.

    Source omissions are separate from effective unavailable timestamps. Partial
    overrides remain valid, and suspicious time ordering is advisory only.
    Source-controlled labels and identities are never rendered as Markdown.
    """
    tables = tuple(item for item in existing if item.timetable_id != table.timetable_id)
    tables += (table,)
    candidate_days = tuple(sorted(row.day for row in table.days))
    lines = ["**Ramadan validation after this approval**"]
    if settings.mode == "on":
        lines.append(
            "Activation: manual on. **Ramadan stays active until switched off; "
            "saved confirmation dates do not limit manual activation.**"
        )
    elif settings.mode == "off":
        lines.append("Activation: off. Ramadan overrides are disabled.")
    elif settings.confirmed_start is None:
        lines.append(
            "Activation: automatic, with no confirmed dates. Ramadan overrides are inactive."
        )
    else:
        lines.append(
            "Activation: automatic, within the adjusted confirmed window only."
        )

    window = None
    if settings.confirmed_start is not None:
        shift = timedelta(days=settings.date_adjustment)
        start = settings.confirmed_start + shift
        end = settings.confirmed_end + shift
        window = tuple(
            start + timedelta(days=offset) for offset in range((end - start).days + 1)
        )
        lines.append(
            f"Adjusted confirmed window: **{start.isoformat()} to {end.isoformat()}** "
            f"({len(window)} dates; adjustment {settings.date_adjustment:+d} days). "
            "Source rows keep their exact Gregorian dates."
        )
        outside = tuple(day for day in candidate_days if not start <= day <= end)
        lines.append(_date_count("Candidate dates outside the saved window", outside))

    if settings.mode == "on" or window is None:
        days = candidate_days
        lines.append(
            f"Review scope: the candidate's **{len(days)} supplied dates** only. "
            "Full Ramadan coverage cannot be assessed from this scope."
        )
    else:
        days = window
        lines.append(f"Review scope: all **{len(days)} adjusted confirmed dates**.")

    if table.kind == "ramadan" and settings.source_id not in {
        None,
        table.timetable_id,
    }:
        lines.append(
            "**This candidate is excluded by the explicitly selected Ramadan source. "
            "Approval does not change that selection.**"
        )

    omissions = sum(len(PrayerField) - len(row.times) for row in table.days)
    lines.append(
        f"Source omissions: **{omissions} field values** across {len(table.days)} supplied rows. "
        "An omitted source field may retain an annual value; it is not necessarily unavailable."
    )
    if table.kind == "ramadan":
        source_conflicts: dict[str, list[date]] = {
            label: [] for _, _, label in _ORDER_CHECKS
        }
        for row in sorted(table.days, key=lambda row: row.day):
            for warning in _time_warnings(row):
                source_conflicts[warning].append(row.day)
        lines.extend(_warning_lines(source_conflicts, "Source time-order warnings"))
    ramadan_dates = []
    annual_dates = []
    no_data = []
    unresolved = []
    inherited = Counter()
    unavailable = Counter()
    iftar_defaults = []
    taraweeh_defaults = []
    conflicts: dict[str, list[date]] = {label: [] for _, _, label in _ORDER_CHECKS}
    for day in days:
        try:
            effective = resolve_day(day, tables, settings)
        except ValueError:
            unresolved.append(day)
            continue
        if effective.ramadan_row is not None:
            ramadan_dates.append(day)
        elif effective.annual_row is not None:
            annual_dates.append(day)
        if effective.row is None or not effective.row.times:
            no_data.append(day)
        override_fields = (
            effective.ramadan_row.times if effective.ramadan_row is not None else {}
        )
        annual_fields = (
            effective.annual_row.times if effective.annual_row is not None else {}
        )
        inherited.update(
            field for field in annual_fields if field not in override_fields
        )
        values = effective.row.times if effective.row is not None else {}
        unavailable.update(field for field in PrayerField if field not in values)
        if (
            effective.ramadan_active
            and PrayerField.IFTAR in values
            and PrayerField.IFTAR not in annual_fields
            and PrayerField.IFTAR not in override_fields
        ):
            iftar_defaults.append(day)
        if effective.ramadan_active and PrayerField.TARAWEEH not in values:
            taraweeh_defaults.append(day)
        if effective.row is not None:
            for warning in _time_warnings(effective.row):
                conflicts[warning].append(day)

    lines.extend(
        (
            "Effective counts below reflect the current activation mode and source selection.",
            _date_count("Dates with an active Ramadan source row", ramadan_dates),
            _date_count("Dates using annual data without a Ramadan row", annual_dates),
            _date_count("Dates with no effective prayer timestamps", no_data),
            "Annual field values retained (number of reviewed dates): "
            + _field_counts(inherited),
            _date_count(
                "Iftar defaults to effective Maghrib beginning", iftar_defaults
            ),
            _date_count("Taraweeh is text only: After Isha Jamaat", taraweeh_defaults),
            "Unavailable timestamps after merging and defaults (number of reviewed dates): "
            + _field_counts(unavailable),
        )
    )
    if unresolved:
        lines.append(
            "**Cannot resolve overlapping or inconsistent sources on some review dates. "
            "Those dates are excluded from the effective counts.**"
        )
        lines.append(_date_count("Unresolved dates", unresolved))
    lines.extend(_warning_lines(conflicts, "Effective time-order warnings"))
    return "\n\n".join(lines)
