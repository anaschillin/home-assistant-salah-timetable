# Compare a pending timetable with the approved source

**Milestone 17.** The Options flow includes a read-only **Compare changes
before approval** choice on the pending import review form. The comparison
never activates a staged timetable. You may page through differences,
return to review and explicitly **Approve** or **Reject**. Leaving the form
keeps the pending import; reopening **Review pending import** resumes it.

## Comparison scope

The comparison uses the exact timetable source ID that Home Assistant will replace
on approval, usually its kind and year. This is a **whole-source replacement**,
not a merge of partial months. All dates in a legacy multi-year source are included.
Other source IDs, other mosques and separately approved Ramadan tables are untouched.

- **Added date:** the pending source includes a date absent from the old source.
  Its explicitly published values are listed as field additions; they may span pages.
- **Removed date:** an old source date is absent from the proposed replacement.
  Approval removes that source date; the comparison does **not** invent values.
- **Time changed:** both versions contain the field but its canonical HH:MM
  values differ. Multiple Friday Jumu'ah congregations are compared as ordered
  sequences; none are silently collapsed.
- **Field added / removed:** an explicit published value appears or disappears
  on a date present in both versions. A missing field is **absent**, not 00:00.
- **Additional original-cell changes:** retained source text or unmapped cells
  change beyond the canonical field differences. Original cells are escaped and
  bounded for display, and URL-shaped tokens are redacted.
- **No canonical changes:** the published values match, even if PDF/CSV bytes,
  mapping, original tokens or provenance have changed. Inspect the full source
  before approving; this is not a claim that the source files are identical.

Date and field rows are ordered deterministically. Each comparison page includes
at most **10 entries** and gives the current page number. Use **Next page**,
**Previous page**, or **Return to approval/rejection** to navigate.

## Safety, privacy and limits

The review displays explicit canonical published values in the authenticated
Home Assistant Options UI. Original source text, URLs, validators, file bodies
and private imported data are **not** written to logs or diagnostics by the
comparison. No effective Ramadan fallbacks, calculated Hijri dates or time-zone
conversions are mixed into the source comparison. Exact original tokens remain
stored separately as source provenance for approval and troubleshooting.

Pending proposals are still bound to a stage ID. If another flow rejects or
replaces the proposal, a stale review or comparison cannot activate it. If the
approved baseline for the target source changes, the comparison refreshes and
returns to its first page. Approval also rechecks that baseline from disk under
the shared storage lock and requires another decision after a change. Existing
atomic storage approvals, Ramadan validation and rejection semantics remain
authoritative. See [the full import-review guide](import_review.md) for retained
tokens, provenance limitations and baseline behavior.

For a large publication, inspect **every page** as well as its original PDF/CSV
before approving. This feature presents published-value and source differences; it does
not assess copyright, source authenticity or religious accuracy.
