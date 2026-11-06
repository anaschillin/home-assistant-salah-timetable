# Documentation Simplification — Action Plan

**Status:** First guide simplification pass merged; this is the maintained audit and follow-up list.

**Audit baseline:** Initial guide audit against `main` on 1 November 2026; card/editor screenshot refresh verified against merged `main` on 4 November 2026.

**Scope:** All 37 tracked Markdown documents: root guidance, user/contributor guides, shared excerpts, research notes, examples and test/fixture READMEs.

**Owner / execution:** A maintainer or Codex following [AGENTS.md](../AGENTS.md).

The readiness and import features, documentation plan and first guide cleanup are
already merged. The stable 1.0.0 release is published. Do not restart those tasks
or wait for their old PRs to merge. The [roadmap](roadmap.md) contains future
product work; this file records documentation ownership and concrete remaining
work. The original guide screenshot pass is merged; this latest card/editor gallery refresh remains proposed until its PR merges.

## Starting conditions

- Inspect current `main`, open PRs, `versions.toml`, the published release and the implementation before changing a claim.
- Start new work from updated `main`, or continue the existing documentation branch when the user asks to extend its PR. Preserve concurrent changes.
- Distinguish shipped features, changes proposed on a branch and research-only ideas. A current version marker is not proof that every file on `main` is included in that version's tag.
- Keep historical changelog and source-research evidence historical; correct current status without rewriting past results.

## Outcomes and non-negotiable requirements

- Help users install, import, explicitly approve a timetable, configure a card and use automations without reading implementation internals.
- Preserve published Salah/Jamaat values, missing-data handling, timezone rules and exact-date approval/replacement semantics.
- Keep source bounds, PDF layout restrictions, cross-year/downgrade limits and Ramadan activation explicit.
- Keep date coverage distinct from required-field completeness, calculated Hijri display distinct from observed Ramadan dates, and research distinct from runtime features.
- Change documentation to match the implementation; report code discrepancies separately rather than changing runtime behaviour during an audit.
- Retain stable headings, links, shared excerpt/version markers and image provenance. Use existing guides rather than introducing parallel reference pages.

## File-by-file backlog

The audit reviewed every tracked Markdown file, including unchanged documents.
Implementation checks used the config/source/import flows, parsers, persistence,
sensors/calendar, domain resolvers, card/editor, blueprints, version tooling,
release scripts and all workflow definitions. Local links, heading anchors,
HTML image references and documented file inventories are checked separately.

| Documents | Audit result / action |
| --- | --- |
| `README.md` | Keep the concise install/navigation entry point; name both coverage and completeness alerts. Recommend direct HACS catalogue installation; retain custom-repository and manual release-copy fallbacks. |
| `AGENTS.md` | Replace obsolete unmerged-feature prerequisites with current-branch/release verification; align heading rules with Contributing. |
| `CHANGELOG.md` | Correct the current release's stale unreleased label against GitHub Releases; retain historical entries and explain old development-snapshot labels. |
| `CONTRIBUTING.md` | Version/excerpt ownership, Linux/WSL setup and browser commands agree with tooling; qualify full CI versus Markdown-only PR validation. |
| `SECURITY.md` | Replace candidate-era maintenance wording with stable-release/development scope; retain private reporting and upstream-pin policy. |
| `docs/getting-started.md` | Setup fields, readiness, approval, card selection, reconfiguration and deletion match the flows; retain the task screenshots and separate completeness from coverage. |
| `docs/import_review.md` | Cross-year CSV, mapping suggestions, removed-date warnings and rollover are implemented. Correct rollover eligibility/year derivation, PDF fallback precedence and manual-upload Source status; remove attachment-session/live-URL diary text. |
| `docs/dashboard.md` | Defaults and seven editor groups agree with the card; distinguish supported YAML/legacy options from graphical controls and document optional title. History switches remain disabled. |
| `docs/automations.md` | All 27 sensors, calendar and six blueprints checked; include selected media players among required Adhan inputs. Keep timestamp and activation limits. |
| `docs/architecture.md` | Module inventory agrees with production files; clarify that only PDF extraction is subprocess-isolated and remove obsolete publication-URL status. |
| `docs/testing.md` | Python/Node counts, coverage gates, compatibility pairs and commands match the repository. Include all release workflows in the CI ownership table and correct stale link labels. |
| `docs/releasing.md` | Automatic publication is implemented. Correct same-version reconciliation claims; remove workflow-installation prerequisites and dated acceptance diary text, document the completed catalogue listing and ongoing maintenance and keep candidate evidence in PR/release reviews. |
| `docs/roadmap.md` | Remove old unmerged-PR prerequisites and distinguish implemented import/readiness features from further usability work. |
| `docs/documentation-simplification-plan.md` | Replace the unstarted proposal with this audit, completed scope, ownership and specific remaining work. |
| `docs/asset-provenance.md` | Keep inventory ownership, separate photograph rights and screenshot redaction/resampling disclosure; distinguish current-tree removal from Git-history removal. |
| All four `docs/_excerpts/*.md` files | Installation, support, standard development commands and validation boundaries remain canonical; regenerate consumers after excerpt edits. |
| `examples/README.md` | Two-day synthetic CSV instructions agree with the example; retain its fictional-data and partial-year warning. |
| `tests/README.md` and all ten `tests/<area>/README.md` files | Ownership and focused commands checked against actual modules. Include completeness/health alerts and both release-script Node suites; clarify that missing dates stay explicit in month data. |
| All four fixture READMEs under `tests/fixtures/` | CSV/PDF generators, expected-value files and frozen storage schemas match their provenance. Preserve historical serializer identities; do not regenerate legacy fixtures from current code. |
| Both `research/islamic-history/*.md` audits | Dated source research and proposed event delivery remain explicitly research-only. Do not promote candidates, historical source counts or permission claims into current runtime guarantees. |

## Completed user-guide scope

These items are present in the merged implementation and guides, rather than
unstarted product proposals:

- [x] Readiness status, today/tomorrow coverage, readable missing-field names/counts and settings/import/review shortcuts.
- [x] Task-specific PDF, CSV and HTTPS import guidance, strict supported-layout descriptions, mapping, comparison and explicit approval.
- [x] Bounded manual cross-year CSV, whole-source replacement and removed-date warnings.
- [x] Previously approved matching manual-CSV mapping suggestions, with user review and conflict suppression.
- [x] Guided annual URL rollover, per-mosque template, editable generated address and explicit approval.
- [x] Seven card-editor groups, detail-level comparison, date navigation, monthly/export/source tools, kiosk and calculated-night controls.
- [x] Separate field-completeness and date-coverage diagnostics/alerts, with one entity reference.
- [x] Shorter contributor/release references linking to canonical test and acceptance procedures.
- [x] Verified default HACS catalogue listing, with catalogue-first installation instructions and both custom-repository and manual release-copy fallbacks.

The earlier merged documentation pass added setup/import/settings screenshots
and anonymised desktop/mobile card examples. The new device gallery includes
16 fresh desktop, mobile and tablet screenshots from a configured real mosque;
those newer captures are not anonymised. Treat all interface screenshots as
illustrative, not independently verified timetable publications. See the
[asset provenance guide](asset-provenance.md) for screenshot and photo rights.

## Remaining documentation work

- [ ] Add captures for readiness with named missing fields, CSV mapping suggestions, removed-date warnings and comparison filtering when suitable redacted examples are available; the supplied review summary is not a comparison-screen capture.
- [ ] Consider generating the long test-module inventory from its existing ownership checks; keep the inventory guard and coverage requirements intact. Changes to tooling need their own reviewed implementation.
- [ ] Evaluate further consolidation of architecture, testing and release references only where a specific duplicate remains. Preserve the complete module inventory, exact commands and internal rule audit.
- [x] Stable-release same-version reconciliation: subsequent `main` commits now skip an existing published stable version while preserving immutable tags and rejecting collisions; see the release guide and regression tests.
- [ ] On later releases, recheck screenshots, form labels, defaults, source bounds, compatibility pins and research/runtime separation against the actual release tag.

## Canonical document ownership

| Subject | Source of truth |
| --- | --- |
| Summary and installation entry | `README.md` |
| First-time journey, setup and common issues | `docs/getting-started.md` |
| Source formats, mapping, validation, comparison and approval | `docs/import_review.md` |
| Card/editor options, display and troubleshooting | `docs/dashboard.md` |
| Entities, automations, calendar and alerts | `docs/automations.md` |
| Modules and data lifecycle | `docs/architecture.md` |
| Test process and inventory | `docs/testing.md`, with brief test-area READMEs |
| Release workflow, acceptance and internal quality audit | `docs/releasing.md` |
| Versions and contributor workflow | `versions.toml` and `CONTRIBUTING.md` |
| Shared installation/support/check excerpts | `docs/_excerpts/` |
| Licences and asset/fixture rights | `docs/asset-provenance.json` and `docs/asset-provenance.md` |
| Future product work | `docs/roadmap.md` |
| Unapproved historical-event research | `research/islamic-history/` |

## Codex implementation sequence

1. Rebaseline against current `main`, the release tag and open documentation PRs; identify concrete stale claims instead of repeating completed work.
2. Update the canonical guide or excerpt, then regenerate consumers. Preserve technical and safety constraints while simplifying navigation.
3. Check links, heading fragments, images, version/excerpt markers, module inventories and asset integrity. Review the final diff for unintended runtime changes.
4. Report findings, fixes, checks and specific remaining work in the documentation PR. Leave it open for review; do not merge, tag, publish or delete branches without authorisation.

## Validation and definition of done

- [x] All tracked documentation has been reviewed against its canonical implementation or historical evidence; current claims do not rely on obsolete PR status.
- [x] Local file links, heading anchors, HTML image references, shared excerpts and generated version fields resolve.
- [x] `python scripts/sync_documentation.py --check`, `python scripts/sync_versions.py --check` and `python scripts/check_asset_provenance.py --require-cleared` pass.
- [ ] Suite-inventory/provenance checks and applicable CI pass on the final candidate. Keep run-specific evidence in the PR rather than turning guides into a validation diary.
- [x] Remaining work is explicit and does not describe completed features as future work. Research notes and old changelog snapshots remain clearly historical.

**Out of scope:** runtime changes, new product features, publication discovery,
religious/date certification, licensing decisions and creating releases.
