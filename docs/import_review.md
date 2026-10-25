# Review an import's changes

Every PDF, CSV or URL proposal still requires an explicit **Approve and save
timetable** decision. The review compares the proposal with the currently approved
source it will replace, in addition to the existing coverage, warnings, sample values
and Ramadan review. A changed download is never activated automatically.

## Replacement scope

The comparison uses the proposal's exact source ID, usually its kind and year such
as `annual-2026`. Approval replaces that entire source. It does not merge only the
dates supplied by the proposal, and it does not compare against an unrelated year or
another source whose dates happen to overlap. If a legacy source contains several
years, the comparison includes all dates in that source, so dates removed by a
replacement remain visible. Other source IDs remain stored.

Check added and removed dates as well as changed times. A shorter replacement can
remove previously available prayers or dates even when its first sample rows look
correct. An initial import has no previous source: its dates and published values
are additions.

## Published values and source details

The comparison reports canonical published values by Gregorian date and prayer
field. It retains every Jumu’ah congregation in the field's ordered time list.
Each difference shows the previous and proposed value in 24-hour format; a missing
published value is labelled **absent**. Removing a field never fills it from another
date. The counts treat one field on one date as one entry, including a Jumu’ah list
with several congregations.

This comparison concerns the imported source. Effective Ramadan overrides and the
documented Maghrib-to-Iftar fallback are assessed separately in the Ramadan review.
A source value can be absent while an approved annual value or effective fallback
still supplies a dashboard event. The change comparison does not rewrite either
the publication or the Ramadan settings.

Source details identify changes to retained original tokens and available parser,
format, mapping, checksum and publication-profile metadata. Original text is escaped
for display; long displayed tokens are truncated and URLs are omitted from this
comparison. Retained original cells remain in protected import provenance; keep the
publication available when checking them.
A changed source file or checksum can have unchanged canonical prayer
values: it may contain different notes, labels or document structure. That is not
a guarantee that only formatting changed. Where an older stored source lacks its
original provenance, the review identifies that limitation rather than inventing
previous text or metadata.

## Browse and decide

Choose **Compare changes before approval** on the review form. The read-only
comparison is paginated in groups of ten entries, including date additions/removals,
canonical field differences and additional original-cell changes. Use **Next page**
and **Previous page** to inspect the lists. Each choice appears when that page
exists. Navigation does not approve, reject or replace the proposal. The summary
counts cover the full comparison, including changes on other pages. Choose
**Return to approval/rejection** to return to the review form, then explicitly
**Approve and save timetable** or **Reject and keep the active timetable**.
Approve only after checking the publication and the complete replacement scope.

Closing the review keeps its staged proposal for **Configure → Review pending
import**, including after a restart. The page position is a temporary UI choice and
resets when a new review flow opens. Rejection removes the staged proposal and keeps
the approved records. A save failure keeps the prior approved snapshot.

If the approved source changes while your review is open, approval is stopped. The
review refreshes the comparison against the new approved baseline, returns to the
first page and requires a new approval decision. Changes to another source ID or
another mosque do not invalidate this baseline. A decision from an older preview
cannot silently overwrite a source you did not review. If another proposal replaces the staged identity, or the
integration reloads while the flow is active, reopen the current pending review.
