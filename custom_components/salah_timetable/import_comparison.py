"""Pure, paged comparison of one whole-source timetable replacement."""

import re
from dataclasses import dataclass
from datetime import date, time
from html import escape

from .import_model import ImportCandidate
from .model import DailyPrayers, PrayerField, Timetable

DEFAULT_PAGE_SIZE = 10
_FIELD_ORDER = {field: position for position, field in enumerate(PrayerField)}
_URL = re.compile(r"\b(?:[a-z][a-z0-9+.-]*://|www\.)\S+", re.IGNORECASE)


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
    table = candidate.timetable
    if previous is not None and (
        previous.timetable_id != table.timetable_id or previous.kind != table.kind
    ):
        raise ValueError("Comparison needs the same source identity and kind")
    if previous_source is not None and (
        previous is None or previous_source.timetable != previous
    ):
        raise ValueError("Previous provenance must match the approved timetable")
    old_rows = {row.day: row for row in previous.days} if previous else {}
    new_rows = {row.day: row for row in table.days}
    changes = []
    source_changes = []
    for day in sorted(old_rows.keys() | new_rows.keys()):
        old_row, new_row = old_rows.get(day), new_rows.get(day)
        old_times = old_row.times if old_row else {}
        new_times = new_row.times if new_row else {}
        displayed_before = set()
        displayed_after = set()
        for field in PrayerField:
            before, after = old_times.get(field, ()), new_times.get(field, ())
            if before == after:
                continue
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
        tuple(sorted(new_rows.keys() - old_rows.keys())),
        tuple(sorted(old_rows.keys() - new_rows.keys())),
        tuple(changes),
        tuple(source_changes),
    )


def _safe(value: str, limit: int = 180) -> str:
    """Bound source-controlled tokens and escape Markdown/HTML without URLs."""
    value = _URL.sub("[URL omitted]", value)
    truncated = len(value) > limit
    value = escape(value[:limit]).replace("\n", " ").replace("\r", " ")
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#", "~"):
        value = value.replace(character, "\\" + character)
    return value + (" … [truncated; inspect retained source]" if truncated else "")


def _values(values: tuple[time, ...]) -> str:
    return (
        ", ".join(value.strftime("%H:%M") for value in values) if values else "absent"
    )


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
