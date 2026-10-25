"""Read-only, source-scoped comparisons for staged timetable replacements.

Never merge dates across sources or infer missing times from Ramadan fallbacks.
Only immutable canonical published values are compared; originals stay stored
with their respective candidates for later provenance inspection.
"""

from dataclasses import dataclass
from datetime import date

from .model import DailyPrayers, PrayerField, Timetable

DIFF_PAGE_SIZE = 20


@dataclass(frozen=True)
class ImportChange:
    """One source-date addition/removal or one changed field on a shared date."""

    day: date
    kind: str
    field: PrayerField | None
    before: tuple[str, ...]
    after: tuple[str, ...]


@dataclass(frozen=True)
class ImportDiff:
    """A complete bounded source comparison; pages affect presentation only."""

    changes: tuple[ImportChange, ...]
    added_dates: int
    removed_dates: int
    changed_fields: int
    added_fields: int
    removed_fields: int
    previous_exists: bool

    @property
    def page_count(self) -> int:
        return max(1, (len(self.changes) + DIFF_PAGE_SIZE - 1) // DIFF_PAGE_SIZE)


def _values(row: DailyPrayers) -> dict[PrayerField, tuple[str, ...]]:
    return {
        field: tuple(value.strftime("%H:%M") for value in times)
        for field, times in row.times.items()
    }


def _full_row(row: DailyPrayers) -> tuple[str, ...]:
    values = _values(row)
    return tuple(
        f"{field.value}: {', '.join(values[field])}"
        for field in sorted(values, key=lambda item: item.value)
    )


def compare_timetables(proposed: Timetable, approved: Timetable | None) -> ImportDiff:
    """Compare only the exact replaced source, not effective/mixed year values."""
    if approved is not None and (
        proposed.timetable_id != approved.timetable_id or proposed.kind != approved.kind
    ):
        raise ValueError("Cannot compare different timetable source identities")

    previous = {row.day: row for row in approved.days} if approved else {}
    current = {row.day: row for row in proposed.days}
    changes: list[ImportChange] = []
    added_dates = removed_dates = changed_fields = added_fields = removed_fields = 0

    for day in sorted(previous.keys() | current.keys()):
        old, new = previous.get(day), current.get(day)
        if old is None:
            added_dates += 1
            changes.append(ImportChange(day, "date_added", None, (), _full_row(new)))
            continue
        if new is None:
            removed_dates += 1
            changes.append(ImportChange(day, "date_removed", None, _full_row(old), ()))
            continue
        before, after = _values(old), _values(new)
        for field in sorted(before.keys() | after.keys(), key=lambda item: item.value):
            prior, updated = before.get(field, ()), after.get(field, ())
            if prior == updated:
                continue
            if not prior:
                kind = "field_added"
                added_fields += 1
            elif not updated:
                kind = "field_removed"
                removed_fields += 1
            else:
                kind = "field_changed"
                changed_fields += 1
            changes.append(ImportChange(day, kind, field, prior, updated))

    return ImportDiff(
        tuple(changes),
        added_dates,
        removed_dates,
        changed_fields,
        added_fields,
        removed_fields,
        approved is not None,
    )


def diff_overview(diff: ImportDiff) -> str:
    """Small summary for the approval form, without copying source content."""
    if not diff.previous_exists:
        return (
            f"New source: {diff.added_dates} dates to add; no existing approved "
            "version of this source will be replaced."
        )
    if not diff.changes:
        return (
            "No changes to canonical published times or availability. "
            "Source bytes, original tokens or provenance may still differ."
        )
    return (
        f"Changes to this source: **{diff.added_dates} dates added**, "
        f"**{diff.removed_dates} dates removed**; "
        f"**{diff.changed_fields} times changed**, "
        f"**{diff.added_fields} fields added**, "
        f"**{diff.removed_fields} fields removed**. "
        "Review every page before approving: an omitted date or field stays absent."
    )


def render_diff_page(diff: ImportDiff, page: int) -> str:
    """A small explicit-values page: no source URLs or untrusted original tokens."""
    if not 0 <= page < diff.page_count:
        raise ValueError("Invalid comparison page")
    lines = [
        diff_overview(diff),
        f"**Comparison page {page + 1} of {diff.page_count}**",
    ]
    if not diff.changes:
        lines.append("No canonical date or field changes to display.")
    for change in diff.changes[page * DIFF_PAGE_SIZE : (page + 1) * DIFF_PAGE_SIZE]:
        day = change.day.isoformat()
        if change.kind == "date_added":
            lines.append(f"- **+ {day} (date added):** {'; '.join(change.after)}")
        elif change.kind == "date_removed":
            lines.append(f"- **− {day} (date removed):** {'; '.join(change.before)}")
        else:
            old = ", ".join(change.before) if change.before else "absent"
            new = ", ".join(change.after) if change.after else "absent"
            lines.append(f"- **{day} · {change.field.value}:** {old} → {new}")
    lines.append(
        "Only the pending timetable is compared with the approved version of "
        "this exact source. Other years, sources and effective Ramadan fallbacks "
        "are not included. Returning to review does not approve anything."
    )
    return "\n\n".join(lines)
