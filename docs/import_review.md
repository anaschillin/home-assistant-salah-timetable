# Review and compare an imported timetable

Every PDF, CSV or URL proposal requires an explicit **Approve and save timetable**
decision. Nothing is activated automatically, including a changed publication
download. The review includes date coverage, missing fields, warnings, sample
values, Ramadan effects, and an optional read-only comparison against the
currently approved publication.

## Replacement scope

A comparison targets the **exact source ID** that approval will replace (for
example, `annual-2026`), not an unrelated timetable with overlapping dates.
Approving a replacement changes the **whole source**, not just the dates
displayed in the preview. Separate approved source IDs, other mosques and
separately approved Ramadan tables are unchanged. A legacy source containing
multiple years is compared across all of its dates.

An initial import has no previous source: its published dates and values are
additions. Before replacing any existing source, check whether a shorter
publication removes previously available dates or prayers.

## Understanding the changes

The comparison uses the original source's **canonical published** prayer values,
indexed by Gregorian date and prayer field. Times are displayed as 24-hour
HH:MM. Every published Friday Jumu’ah congregation remains in its ordered
sequence, not just the first time.

| Difference | Meaning |
| --- | --- |
| Added date | A date is present only in the new source; its published fields are also additions |
| Removed date | A date is present only in the approved source and would be removed on replacement |
| Changed time | Both sources publish a field but its canonical time or ordered Jumu’ah list differs |
| Added or removed field | An explicit published value appears or disappears on an existing date; missing is **absent**, never `00:00` |
| Additional original-cell change | Retained text or unmapped source cells differ beyond the canonical prayer values |
| No canonical changes | Published prayer values agree, although the file, provenance, checksum or original text may still differ |

One field on one date counts as a single changed entry, even when Jumu’ah
contains multiple times. Date and field ordering is deterministic.

Source details may also identify differences in available parser, time format,
column mapping, checksum or publication-profile metadata. Retained original
tokens are escaped and truncated for safe display; URL-shaped text is redacted
and actual download URLs are not included. Where older stored records lack
original provenance, the UI reports the limitation rather than inventing the
previous values.

**A matching canonical timetable does not prove that two source files are
identical.** Changes in notes, labels, original cells or layout still require
review of the actual mosque publication.

## Ramadan and calculated values

The source comparison shows what was **printed and imported**, not derived
dashboard values. Effective Ramadan overrides, the documented Maghrib-to-Iftar
fallback and other approved annual sources are evaluated separately in the
Ramadan review. No calculated Hijri dates, time-zone conversions or effective
fallbacks are inserted into the published-value comparison. The comparison
never rewrites the publication or Ramadan settings.

## Browse, approve or reject

1. In the pending import review, choose **Compare changes before approval**.
2. Inspect **every page** of additions, removals, canonical field differences
   and extra original-cell changes. Each page contains at most **10 entries**.
   **Next page** and **Previous page** are available where applicable;
   summary counts cover the full comparison.
3. Choose **Return to approval/rejection**. The comparison does not save,
   reject or replace anything. Explicitly select **Approve and save timetable**
   or **Reject and keep the active timetable**.

Closing the review retains the staged proposal under **Configure → Review
pending import**, including after a Home Assistant restart. The current page
position is temporary and resets when a new review flow opens. Rejection
removes the pending proposal but preserves approved data. A failed save leaves
the approved snapshot intact.

If the approved baseline for the target source changes during review, the
comparison refreshes, returns to its first page and requires another explicit
approval. Changes to unrelated source IDs or other mosques do not invalidate
this baseline. Approval checks the baseline again under the shared storage
lock; an old preview cannot silently overwrite a changed source. If the
pending stage is rejected/replaced, or the integration reloads mid-flow,
reopen the current pending review before deciding.

## Security and limitations

The comparison is displayed in the authenticated Home Assistant Options UI.
Private source bodies, URLs, original cells, validators and published times
are **not logged or exposed through diagnostics** by this comparison; stored
source provenance remains protected. Existing atomic storage approvals and
Ramadan validation remain authoritative.

Inspect the complete original PDF/CSV as well as **all** pages before
approving. Comparison does **not** assess copyright, religious authenticity,
source accuracy or redistribution permission.
