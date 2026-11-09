"""Bounded, escaped human-readable previews of imported prayer schedules."""

from html import escape

from ..domain.ramadan import RamadanSettings
from ..domain.ramadan_validation import ramadan_review


def _safe_text(value: str) -> str:
    """Do not let imported labels become Markdown or HTML in the preview."""
    value = escape(value[:500])
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#"):
        value = value.replace(character, "\\" + character)
    return value.replace("\n", " ").replace("\r", " ")


PDF_LAYOUT_LABELS = {
    "pdf_table_v1": "Supported sample text-table PDF",
    "pdf_spaced_v1": "ISO-dated spaced text-table PDF",
    "mosque_a_annual_v1": "Mosque A annual calendar",
    "mosque_a_monthly_v1": "Mosque A monthly calendar",
    "mosque_b_annual_v1": "Mosque B Masjid annual calendar",
    "mosque_b_ramadan_v1": "Mosque B Masjid separate Ramadan page",
}


def import_summary(candidate, existing, settings=None) -> str:
    """Bounded, explicit review of coverage, missing fields and replacement."""
    coverage = candidate.coverage
    table = candidate.timetable
    lines = [
        f"**{table.kind.title()} {candidate.year}** · {coverage.row_count} dated rows",
        f"Dates: {coverage.start_date.isoformat()} to {coverage.end_date.isoformat()}",
        f"SHA-256: `{candidate.sha256}`",
        f"Format: {candidate.time_format}. Date column: {_safe_text(candidate.date_column)}.",
        "Columns: "
        + "; ".join(
            f"{_safe_text(source)} → {field}"
            for source, field in candidate.columns.items()
        ),
        f"Missing dates{' within the supplied span' if table.kind == 'ramadan' or table.timetable_id.endswith('-cross-year') else ''}: **{len(coverage.missing_dates)}**.",
    ]
    if candidate.source_format == "pdf":
        lines.append(
            "Recognized PDF: **"
            + PDF_LAYOUT_LABELS.get(candidate.parser_id, "Unsupported layout")
            + "**. Review the printed dates and every mapped prayer time."
        )
    if coverage.missing_fields:
        lines.append(
            "Fields absent from this source (number of rows): "
            + ", ".join(
                f"{key}: {count}" for key, count in coverage.missing_fields.items()
            )
        )
    previous = next(
        (item for item in existing if item.timetable_id == table.timetable_id), None
    )
    lines.append(
        f"Approval replaces **{len(previous.days)} existing rows** for this source."
        if previous
        else "Approval adds this source; other years remain stored."
    )
    if table.timetable_id.endswith("-cross-year"):
        lines.append(
            "This separate cross-year source covers both years in a single approval. "
            "Dates overlapping another ordinary source are rejected; replacing a "
            "source replaces all previously approved dates for the same starting year."
        )
        if previous:
            removed = sorted(
                {row.day for row in previous.days} - {row.day for row in table.days}
            )
            if removed:
                lines.append(
                    f"**Warning: approval removes {len(removed)} previously approved "
                    f"date(s)** from this cross-year source. First removed date: "
                    f"{removed[0].isoformat()}; last removed date: {removed[-1].isoformat()}. "
                    "Use Compare changes to review all removed dates before approval."
                )
    lines.append(
        "Choose **Compare changes** to inspect every canonical and original-cell change "
        "before approval. The comparison never activates a pending import."
    )
    if table.kind == "ramadan":
        lines.append(
            "**Ramadan overrides apply only on confirmed dates or with explicit manual activation in Ramadan settings.**"
        )
    if candidate.parser_id in {"mosque_a_annual_v1", "mosque_a_monthly_v1"}:
        lines.append(
            "MOSQUE_A layout: morning/noon/evening columns are normalized to 24-hour time. "
            "The published Maghrib (Iftaar) value supplies both Jamaat and Iftar; Sunset remains Maghrib beginning. "
            "Friday's shared slot supplies Jumu'ah only. Second-Khutbah notes are not additional Jamaat events. "
            "Hijri dates do not confirm Ramadan activation."
        )
    if candidate.parser_id == "mosque_a_monthly_v1":
        lines.append(
            "MOSQUE_A monthly calendars may include dates outside Ramadan. "
            "The source date range does not confirm the Ramadan date window."
        )
    if candidate.parser_id == "mosque_b_ramadan_v1":
        lines.append(
            "Only the separate Mosque B Ramadan page is imported; annual pages are not imported. "
            "The printed table includes 20 March 2026 (Hijri 1 after Ramadan). "
            "Its 31 rows do not confirm 31 Ramadan dates. "
            "Maghrib beginning supplies default Iftar only when Ramadan is active. "
            "No Maghrib Jamaat, Jumu'ah or Taraweeh timestamp is supplied by this layout."
        )
    if candidate.parser_id == "mosque_b_annual_v1":
        lines.append(
            "Only Mosque B's twelve annual tables are imported; the separate Ramadan page is not imported. "
            "The clipped “May …” date cell is interpreted as **2026-05-01** only after checking "
            "the printed May 2026 heading, Friday weekday and complete sequence of dates 2–31. "
            "The original clipped date is retained. Check this interpretation before approval. "
            "Sehri is published only for February–May; other source months have no Sehri value. "
            "No Maghrib Jamaat, Iftar, Jumu'ah or Taraweeh timestamp is supplied by this layout. "
            "Friday's Zohar Jamaat column keeps its published meaning. "
            "May's Hijri caption is printed as 1446 AH; it is retained without changing the Gregorian 2026 dates. "
            "Printed Hijri headings do not confirm Ramadan dates."
        )
    lines.append("Preview (first three dates; all explicit times on those dates):")
    for row in table.days[:3]:
        values = "; ".join(
            f"{field.value}: {', '.join(value.strftime('%H:%M') for value in times)}"
            for field, times in row.times.items()
        )
        lines.append(f"- {row.day.isoformat()} — {values}")
    if candidate.warnings:
        lines.append("Validation warnings:")
        lines.extend(
            f"- {_safe_text(warning.replace('Missing times will remain unavailable.', 'Missing source fields remain absent from this import. Effective Ramadan availability is shown separately.'))}"
            for warning in candidate.warnings[:10]
        )
    settings = settings or RamadanSettings()
    if table.kind == "ramadan" or settings.mode == "on" or settings.confirmed_start:
        lines.append(ramadan_review(table, existing, settings))
    lines.append(
        "Approve only after checking these values against the published timetable."
    )
    return "\n\n".join(lines)


