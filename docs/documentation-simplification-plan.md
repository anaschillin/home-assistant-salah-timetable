# Documentation Simplification — Action Plan

**Status:** Core documentation simplification completed; documentation CI has been strengthened. Remaining work is optional redacted examples and recurring release checks.

**Audit baseline:** All 37 Markdown files originally reviewed on 1 November 2026; the original 37-file audit completed on 1 November; release-status entries rechecked against the published `v3.1.0` tag on 7 November 2026.

**Scope:** All 37 tracked Markdown documents: root guidance, user/contributor guides, shared excerpts, research notes, examples and test/fixture READMEs.

**Owner / execution:** A maintainer or Codex following [AGENTS.md](../AGENTS.md).

The readiness/import changes, first guide simplification, card/editor screenshots,
v3 kiosk redesign, casting fixes and PR #138's card alignment improvements have all shipped in `v3.1.0`.
The previous 1.0.0-era prerequisites and unmerged screenshot disclaimer are obsolete.
Do not reopen completed work. The [roadmap](roadmap.md) contains *upcoming product
features only*; this file tracks the documentation audit and residual work.

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

## File-by-file completion record

All **37 tracked Markdown files** were reviewed in the initial simplification
pass; current version/PR statuses are updated through the v3.1.0 release.
A checked row means the document's **audit and ownership review** is complete;
it does not claim every optional screenshot or every future release audit is done.

| Documents | Audit | Verified responsibility / retained boundary |
| --- | :---: | --- |
| `README.md` | [x] | Concise feature/install entry point, current v3.1.0 kiosk preview, official HACS catalogue first, custom-repository/manual fallbacks and links to canonical guides. |
| `AGENTS.md` | [x] | Current-main instructions, documentation handoff, unnumbered descriptive headings and no unmerged-feature prerequisites. |
| `CHANGELOG.md` | [x] | Current 3.1.0 release heading and history; older `unreleased` labels are explicitly historical development snapshots. |
| `CONTRIBUTING.md` | [x] | Version/excerpt ownership, Linux/WSL and browser setup; required CI and Markdown-only fast paths distinguished. |
| `SECURITY.md` | [x] | Stable-release scope, private reporting and constrained dependency advisory policy. |
| `docs/getting-started.md` | [x] | Installation, first import, approval, readiness, mosque settings, card usage, deletion and common issues. More optional redacted edge-case captures remain below. |
| `docs/import_review.md` | [x] | PDF/CSV/HTTPS boundaries, cross-year CSV, reviewed mapping suggestions, removed-date warnings and guided annual rollover; source state and approval are distinct. |
| `docs/dashboard.md` | [x] | Released v3 kiosk, card/editor ordering, seven groups, device gallery, YAML-only/legacy options and disabled history switches. |
| `docs/automations.md` | [x] | 27 mosque sensor entries, prayer calendar, six blueprints, explicit timestamp/activation and coverage/completeness distinctions. |
| `docs/architecture.md` | [x] | Production module and data-flow inventory, approved/pending boundary and PDF-only worker isolation. |
| `docs/testing.md` | [x] | Verified 56 Python test modules, frontend suites, supported HA pairs and CI ownership. The source-controlled inventory remains curated. |
| `docs/releasing.md` | [x] | Validated feature/stable pipelines, immutable same-version release reconciliation, HACS catalogue status, manual acceptance and internal Quality Scale audit. |
| `docs/roadmap.md` | [x] | Unreleased product proposals only; shipped features, dependency upkeep, CI and documentation chores are excluded. |
| `docs/documentation-simplification-plan.md` | [x] | Audit record, source-of-truth ownership, accepted decisions, open follow-ups and verification criteria. |
| `docs/asset-provenance.md` | [x] | Maintainer inventory, fixture/photo licensing, screenshot disclosure and current-tree versus history distinctions. |
| Four `docs/_excerpts/*.md` files | [x] | Shared installation, support, development checks and validation boundaries; sync consumers instead of duplicating them. |
| `examples/README.md` | [x] | Synthetic two-day CSV example and partial-year restriction. |
| `tests/README.md` and ten `tests/<area>/README.md` files | [x] | Test ownership, focused commands, alert and release-script suites, and explicit missing dates. |
| Four fixture READMEs in `tests/fixtures/` | [x] | Fixture generators, expected values and frozen historical storage-schema/provenance. |
| Two `research/islamic-history/*.md` notes | [x] | Dated research only; neither source counts nor proposed historical events imply a shipped feature. |

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

The merged screenshot passes added setup/import/settings examples and the
desktop/mobile/tablet card-editor gallery. The v3 kiosk screenshot also shipped.
The newer device captures show a real configured mosque rather than anonymised
data: they illustrate the interface, **not** independently verified published
prayer schedules. See [asset provenance](asset-provenance.md) for rights,
redaction and decorative photograph licences.

## Remaining documentation work and decisions

- [ ] **Optional screenshots:** add suitably redacted captures of readiness with named missing fields, CSV mapping suggestions, removed-date warnings and comparison filtering when representative examples are available. The existing review-summary capture is not a comparison-screen capture. Do not substitute fabricated UI states or expose real timetable owners' data.
- [x] **Test-inventory assessment:** keep the maintained 56-module inventory and its existing ownership checks. Generating the inventory would introduce extra tooling without a demonstrated maintenance failure; revisit only if actual drift appears.
- [x] **Further consolidation assessment:** architecture, testing and release guides have different primary audiences and canonical responsibilities. No remaining cross-guide duplication warrants merging them; preserve the full inventory, reproducible commands and rule-specific audit.
- [x] **Stable release reconciliation:** already implemented; later `main` commits with a published version leave immutable tags intact and report a no-publication result.
- [x] **v3.1.0 baseline refresh:** the published tag was checked; PR #138's single- and paired-panel changes read as released, not proposed. Existing casting work remains in release history.
- [ ] **Recurring release verification:** for every later candidate, compare screenshots, UI labels, defaults, source limits, compatibility pins and research/runtime separation with the **actual release tag**. Record results in that candidate's PR/release rather than treating this recurring duty as permanently complete.

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
- [x] Documentation-only CI now validates generated versions, shared excerpts, local Markdown/HTML links and heading anchors, and asset provenance. Run-specific outcomes still belong in the corresponding PR and exact commit; this plan does not certify later commits.
- [x] The roadmap contains only upcoming product features. The changelog preserves historical entries; research notes remain research-only; unresolved documentation work is separate.

**Out of scope:** runtime changes, new product features, publication discovery,
religious/date certification, licensing decisions and creating releases.
