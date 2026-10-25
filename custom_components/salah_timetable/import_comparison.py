"""Pure comparison of one whole-source timetable replacement.

Canonical summaries and full original-cell reviews share the same source rows
and canonical field comparison. Neither presentation uses effective fallbacks.
"""

import re
from dataclasses import dataclass
from datetime import date, time
from html import escape

from .import_model import ImportCandidate
from .model import DailyPrayers, PrayerField, Timetable

DIFF_PAGE_SIZE = 20
DEFAULT_PAGE_SIZE = 10
_FIELD_ORDER = {field: position for position, field in enumerate(PrayerField)}
_URL = re.compile(r"\b(?:[a-z][a-z0-9+.-]*://|www\.)\S+", re.IGNORECASE)


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
    """Canonical projection; field counts cover dates shared by both sources."""

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


@dataclass(frozen=True)
class SourceToken:
    """The exact mapped CSV/extracted cell, including a published ditto token."""

    column: str
    value: str


@dataclass(frozen=True)
class FieldChange:
    """One field entry; multiple Jumu'ah congregations stay in the same tuple."""

    day: date
    field: PrayerField
    before: tuple[time, ...]
    after: tuple[time, ...]
    before_tokens: tuple[SourceToken, ...]
    after_tokens: tuple[SourceToken, ...]

    @property
    def kind(self) -> str:
        if not self.before:
            return "added"
        return "removed" if not self.after else "changed"


@dataclass(frozen=True)
class OriginalChange:
    """A changed original cell not already displayed beside a field change."""

    day: date
    column: str
    before: str | None
    after: str | None


@dataclass(frozen=True)
class DateChange:
    """Date coverage changes remain visible even for a row with no prayer values."""

    day: date
    added: bool


ComparisonItem = DateChange | FieldChange | OriginalChange


def _item_order(item: ComparisonItem) -> tuple:
    if isinstance(item, DateChange):
        return item.day, 0, 0
    if isinstance(item, FieldChange):
        return item.day, 1, _FIELD_ORDER[item.field]
    return item.day, 2, item.column


def _page_size(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 100:
        raise ValueError("Comparison page size must be between 1 and 100")
    return value


@dataclass(frozen=True)
class ImportComparison:
    """All changes are retained; presentation limits never alter the totals."""

    candidate: ImportCandidate
    previous: Timetable | None
    previous_source: ImportCandidate | None
    added_dates: tuple[date, ...]
    removed_dates: tuple[date, ...]
    changes: tuple[FieldChange, ...]
    source_changes: tuple[OriginalChange, ...]

    @property
    def items(self) -> tuple[ComparisonItem, ...]:
        return tuple(
            sorted(
                (
                    *(DateChange(day, True) for day in self.added_dates),
                    *(DateChange(day, False) for day in self.removed_dates),
                    *self.changes,
                    *self.source_changes,
                ),
                key=_item_order,
            )
        )

    def page_count(self, page_size: int = DEFAULT_PAGE_SIZE) -> int:
        size = _page_size(page_size)
        return max(1, (len(self.items) + size - 1) // size)

    @property
    def added_fields(self) -> int:
        return sum(change.kind == "added" for change in self.changes)

    @property
    def removed_fields(self) -> int:
        return sum(change.kind == "removed" for change in self.changes)

    @property
    def changed_fields(self) -> int:
        return sum(change.kind == "changed" for change in self.changes)

    @property
    def canonical_equal(self) -> bool:
        return self.previous is not None and not (
            self.added_dates or self.removed_dates or self.changes
        )

    @property
    def provenance_changed(self) -> bool | None:
        """Unknown for legacy tables; byte changes need not be prayer changes."""
        if self.previous_source is None:
            return None
        return _provenance(self.previous_source) != _provenance(self.candidate)


def _provenance(candidate: ImportCandidate) -> tuple:
    # URL identity can change, but its value is never rendered. Validators are
    # transport state and are intentionally outside the source comparison.
    return (
        candidate.sha256,
        candidate.source_format,
        candidate.parser_id,
        candidate.time_format,
        candidate.date_column,
        tuple(sorted(candidate.columns.items())),
        candidate.publication_profile_id,
        candidate.source_url,
    )


def _tokens(
    row: DailyPrayers | None,
    source: ImportCandidate | None,
    field: PrayerField,
) -> tuple[SourceToken, ...]:
    if row is None or source is None:
        return ()
    return tuple(
        SourceToken(column, row.original[column])
        for column, mapped_field in sorted(source.columns.items())
        if mapped_field == field and column in row.original
    )


def _comparison_rows(
    proposed: Timetable, approved: Timetable | None
) -> tuple[tuple[date, DailyPrayers | None, DailyPrayers | None], ...]:
    """Keep all dates of this exact source, including legacy multi-year rows."""
    if approved is not None and (
        proposed.timetable_id != approved.timetable_id or proposed.kind != approved.kind
    ):
        raise ValueError("Cannot compare different timetable source identities")
    previous = {row.day: row for row in approved.days} if approved else {}
    current = {row.day: row for row in proposed.days}
    return tuple(
        (day, previous.get(day), current.get(day))
        for day in sorted(previous.keys() | current.keys())
    )


def _canonical_field_changes(
    old: DailyPrayers | None, new: DailyPrayers | None
) -> tuple[tuple[PrayerField, tuple[time, ...], tuple[time, ...]], ...]:
    """Compare immutable published values before any presentation formatting."""
    before = old.times if old else {}
    after = new.times if new else {}
    return tuple(
        (field, before.get(field, ()), after.get(field, ()))
        for field in PrayerField
        if before.get(field, ()) != after.get(field, ())
    )


def compare_import(
    candidate: ImportCandidate,
    previous: Timetable | None,
    previous_source: ImportCandidate | None = None,
) -> ImportComparison:
    """Compare the exact replacement target, never another source or fallback.

    A legacy target may span several years: every old date is compared. Source
    rows and candidates are immutable and remain untouched. No timezone, display
    formatting, activation mode or calculated Ramadan value participates.
    """
    rows = _comparison_rows(candidate.timetable, previous)
    if previous_source is not None and (
        previous is None or previous_source.timetable != previous
    ):
        raise ValueError("Previous provenance must match the approved timetable")
    changes = []
    source_changes = []
    for day, old_row, new_row in rows:
        displayed_before = set()
        displayed_after = set()
        for field, before, after in _canonical_field_changes(old_row, new_row):
            old_tokens = _tokens(old_row, previous_source, field)
            new_tokens = _tokens(new_row, candidate, field)
            changes.append(
                FieldChange(day, field, before, after, old_tokens, new_tokens)
            )
            displayed_before.update(token.column for token in old_tokens)
            displayed_after.update(token.column for token in new_tokens)
        # Every date keeps cells not already exposed by a FieldChange. In
        # particular, new/removed notes and legacy unmapped cells must remain
        # reachable, and a blank original cell differs from an absent cell.
        old_original = old_row.original if old_row else {}
        new_original = new_row.original if new_row else {}
        for column in sorted(old_original.keys() | new_original.keys()):
            before = old_original.get(column)
            after = new_original.get(column)
            represented = (before is None or column in displayed_before) and (
                after is None or column in displayed_after
            )
            if before != after and not represented:
                source_changes.append(OriginalChange(day, column, before, after))
    return ImportComparison(
        candidate,
        previous,
        previous_source,
        tuple(day for day, old, new in rows if old is None),
        tuple(day for day, old, new in rows if new is None),
        tuple(changes),
        tuple(source_changes),
    )


def _time_strings(values: tuple[time, ...]) -> tuple[str, ...]:
    return tuple(value.strftime("%H:%M") for value in values)


def _full_row(row: DailyPrayers) -> tuple[str, ...]:
    return tuple(
        f"{field.value}: {', '.join(_time_strings(row.times[field]))}"
        for field in sorted(row.times, key=lambda item: item.value)
    )


def compare_timetables(proposed: Timetable, approved: Timetable | None) -> ImportDiff:
    """Project canonical changes into the original twenty-entry summary API.

    A whole added/removed date occupies one entry. Field totals count changes
    on shared dates; compare_import additionally counts fields on new/old dates
    and retains every changed original cell for detailed review.
    """
    changes: list[ImportChange] = []
    added_dates = removed_dates = changed_fields = added_fields = removed_fields = 0
    for day, old, new in _comparison_rows(proposed, approved):
        if old is None:
            added_dates += 1
            changes.append(ImportChange(day, "date_added", None, (), _full_row(new)))
            continue
        if new is None:
            removed_dates += 1
            changes.append(ImportChange(day, "date_removed", None, _full_row(old), ()))
            continue
        for field, prior, updated in sorted(
            _canonical_field_changes(old, new), key=lambda item: item[0].value
        ):
            if not prior:
                kind = "field_added"
                added_fields += 1
            elif not updated:
                kind = "field_removed"
                removed_fields += 1
            else:
                kind = "field_changed"
                changed_fields += 1
            changes.append(
                ImportChange(
                    day, kind, field, _time_strings(prior), _time_strings(updated)
                )
            )
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
    """A small canonical-values page without source URLs or original tokens."""
    if type(page) is not int or not 0 <= page < diff.page_count:
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
            lines.append(f"- **{day}** · {change.field.value}: {old} → {new}")
    lines.append(
        "Only the pending timetable is compared with the approved version of "
        "this exact source. Other years, sources and effective Ramadan fallbacks "
        "are not included. Returning to review does not approve anything."
    )
    return "\n\n".join(lines)


def _safe(value: str, limit: int = 180) -> str:
    """Bound source-controlled tokens and escape Markdown/HTML without URLs."""
    value = _URL.sub("[URL omitted]", value)
    truncated = len(value) > limit
    value = escape(value[:limit]).replace("\n", " ").replace("\r", " ")
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#", "~"):
        value = value.replace(character, "\\" + character)
    return value + (" … [truncated; inspect retained source]" if truncated else "")


def _values(values: tuple[time, ...]) -> str:
    return ", ".join(_time_strings(values)) if values else "absent"


def _source_tokens(tokens: tuple[SourceToken, ...], *, present: bool) -> str:
    if tokens:
        return "; ".join(
            f"{_safe(token.column)}: “{_safe(token.value)}”" for token in tokens
        )
    return "original column mapping unavailable" if present else "absent"


def _scope(table: Timetable) -> str:
    days = tuple(row.day for row in table.days)
    years = sorted({day.year for day in days})
    year_text = str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"
    return (
        f"{table.kind.title()} {year_text}; source {_safe(table.timetable_id)}; "
        f"{len(days)} rows; {min(days).isoformat()} to {max(days).isoformat()}"
    )


def _metadata(label: str, candidate: ImportCandidate) -> str:
    columns = "; ".join(
        f"{_safe(column)} → {_safe(field)}"
        for column, field in sorted(candidate.columns.items())
    )
    return (
        f"{label} source: {_safe(candidate.source_format)}, parser {_safe(candidate.parser_id)}, "
        f"time format {_safe(candidate.time_format)}, profile "
        f"{_safe(candidate.publication_profile_id) if candidate.publication_profile_id else 'none'}; "
        f"SHA-256: `{candidate.sha256}`. "
        f"Date column: {_safe(candidate.date_column)}. Columns: {columns}."
    )


def comparison_overview(comparison: ImportComparison) -> str:
    """Summarize full-source scope, provenance and totals without dated entries."""
    lines = [
        "Whole-source replacement: only this source ID is replaced. Other source IDs remain stored. "
        "Values below are canonical published source times in 24-hour format. "
        "They exclude effective Ramadan merging, fallback and display formatting.",
        f"Proposed: {_scope(comparison.candidate.timetable)}.",
        _metadata("Proposed", comparison.candidate),
    ]
    if comparison.previous is None:
        lines.append(
            "First import for this source ID: there is no approved source to replace."
        )
    else:
        lines.append(f"Approved: {_scope(comparison.previous)}.")
        if comparison.previous_source is None:
            lines.append(
                "Previous source provenance is unavailable (legacy timetable). "
                "Its canonical values and retained original cells are still compared."
            )
        else:
            lines.append(_metadata("Approved", comparison.previous_source))
    lines.extend(
        (
            f"Dates added: **{len(comparison.added_dates)}**. "
            f"Dates removed: **{len(comparison.removed_dates)}**.",
            f"Field entries added: **{comparison.added_fields}**. "
            f"Field entries removed: **{comparison.removed_fields}**. "
            f"Field entries changed: **{comparison.changed_fields}**. "
            "Each field counts once per date; a Jumu'ah entry may contain multiple congregations.",
            f"Additional original-cell changes: **{len(comparison.source_changes)}**. "
            "These may be formatting, ditto tokens or other source annotations; they need not change prayer values.",
        )
    )
    if comparison.canonical_equal:
        lines.append("Canonical prayer values and dates are unchanged.")
    if comparison.provenance_changed:
        lines.append(
            "Source bytes or provenance metadata changed. "
            "A different file checksum alone does not mean prayer values changed."
        )
    if comparison.previous_source is not None and (
        comparison.previous_source.source_url != comparison.candidate.source_url
    ):
        lines.append("Source location changed; URLs are omitted.")
    return "\n\n".join(lines)


def render_comparison_page(
    comparison: ImportComparison,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> str:
    """Render one bounded page; all rows remain reachable through pagination."""
    size = _page_size(page_size)
    pages = comparison.page_count(size)
    if type(page) is not int or not 0 <= page < pages:
        raise ValueError("Comparison page is outside the available range")
    lines = [
        f"**Import comparison — page {page + 1} of {pages}**",
        comparison_overview(comparison),
    ]
    items = comparison.items
    first = page * size
    page_items = items[first : first + size]
    if page_items:
        lines.append(
            f"Comparison entries {first + 1}–{first + len(page_items)} of {len(items)}:"
        )
    else:
        lines.append("No dated value or original-cell changes to display.")
    for item in page_items:
        day = item.day.isoformat()
        if isinstance(item, DateChange):
            lines.append(f"- {day} — date {'added' if item.added else 'removed'}.")
        elif isinstance(item, FieldChange):
            label = item.field.value.replace("_", " ")
            lines.append(
                f"- {day} — {label}: **{_values(item.before)} → {_values(item.after)}** "
                f"({item.kind}). Original mapped cells: "
                f"{_source_tokens(item.before_tokens, present=bool(item.before))} → "
                f"{_source_tokens(item.after_tokens, present=bool(item.after))}."
            )
        else:
            before = "absent" if item.before is None else f"“{_safe(item.before)}”"
            after = "absent" if item.after is None else f"“{_safe(item.after)}”"
            lines.append(
                f"- {day} — original cell {_safe(item.column)}: {before} → {after} "
                "(source text; see canonical changes separately)."
            )
    lines.append(
        "Available original files and full tokens remain in protected import provenance. "
        "Long displayed tokens are truncated; URLs are omitted from this comparison."
    )
    return "\n\n".join(lines)
