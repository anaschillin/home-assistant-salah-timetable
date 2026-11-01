# Documentation Simplification — Action Plan

**Status:** Planned; implementation not started.  
**Priority:** User guides first, maintainer references second.  
**Baseline:** Reviewed `main` as of 31 October 2026 and the documentation and changes proposed in [PR #119](https://github.com/anaschillin/home-assistant-salah-timetable/pull/119) and [PR #120](https://github.com/anaschillin/home-assistant-salah-timetable/pull/120).  
**Owner / execution:** Codex or a maintainer following [AGENTS.md](../AGENTS.md).  
**Scope:** Documentation simplification and narrowly scoped documentation-integrity improvements only.

This is the **canonical, actionable task list** for simplifying the Salah Timetable documentation. The [roadmap](roadmap.md) stays a concise list of future product work; this file holds the detailed documentation project. The audit notes and priorities below are proposals based on reviewed branches, **not claims that PR #119 or #120 has already merged**.

## Starting conditions

- [ ] Confirm PR #119 and PR #120 have both merged into `main`. PR #120 is built on #119, so re-check its final files after the merges. Until then, audit and plan only; do not rewrite guides.
- [ ] Verify the latest `main` HEAD, version/release status, `AGENTS.md`, and the actual user interfaces. Do not assume that proposed PR text is already released.
- [ ] Create a **fresh implementation branch from the updated `main`**. Do not implement on this planning/rename PR. Preserve changes made after the review baseline.
- [ ] Run an inventory of existing Markdown pages, headings, incoming links, screenshots and shared excerpt markers; record the sections to keep, shorten, relocate or cross-link.
- [ ] Agree one canonical source for each piece of information and avoid adding new guide files unless an existing guide cannot serve the need.

## Outcomes and non-negotiable requirements

- **Goal:** Help a user install, import/approve a published timetable, set up the card and use automations without reading implementation internals. Help maintainers find technical and release instructions without duplicated material.
- **Not a line-count exercise:** Preserve safety, compatibility, missing-data handling and exact product behaviour even where an explanation must remain lengthy.
- **No runtime changes:** Do not change sensors, import logic, storage, translations, dashboard behaviour, release automation or integrations to match preferred documentation wording. If a discrepancy reveals a code defect, flag it separately.
- **Accuracy:** Always distinguish published Salah and Jamaat times from calculated information, date coverage from field completeness, and staged imports from explicitly approved timetables.
- **Compatibility:** Keep the source-import restrictions, PDF/OCR and layout boundaries, Ramadan activation, source rollover, version and downgrade limitations, and multiple-mosque isolation accurate.
- **Maintenance:** Continue using `versions.toml`, `scripts/sync_versions.py`, `scripts/sync_documentation.py`, `docs/_excerpts/` and `docs/asset-provenance.json` rather than inventing a second system.
- **Project style:** Follow [documentation standards](../CONTRIBUTING.md#documentation-numbering-and-structure). Keep unnumbered Markdown headings, stable links and consistent terminology.

## File-by-file backlog

The approximate sizes refer to the reviewed baseline and must be refreshed after both dependent PRs merge.

| Priority | File | Observed issue | Required improvement |
| --- | --- | --- | --- |
| **High** | [Getting started](getting-started.md) (~150 lines) | Setup, configuration detail, support policy and troubleshooting compete with the quickstart | Organise around the real first-time UI journey; keep detailed settings and long reference rules in their canonical guides |
| **High** | [Import and review](import_review.md) (~500 lines) | Long fixture/parser narratives obscure common PDF/CSV/URL tasks | Use task-focused source-type sections; retain concise supported-layout matrix, mapping, replacement, review and hard limitations |
| **High** | [Dashboard](dashboard.md) (~460 lines) | Settings, implementation detail, backgrounds and legacy configuration are interleaved | Match actual editor groups; one settings/defaults reference; move technical maintenance detail to existing contributor docs |
| **High** | [Automations](automations.md) (~290 lines) | User tasks and broad entity/coverage explanations are mixed | Organise by reminders, Adhan/media, completeness and calendar; maintain one authoritative entity/attribute list |
| **High** | [README](../README.md) | Landing page repeats onboarding/detail from guides | Keep summary, installation entry point, screenshots and concise guide navigation; link to detailed procedures |
| **Medium** | [Testing](testing.md) (~410 lines) | Large manually maintained inventory plus overlapping per-area READMEs | Separate how-to-run from inventories, fixture ownership, compatibility and acceptance; decide whether generating inventory is beneficial |
| **Medium** | [Releasing](releasing.md) (~420 lines) | Operational release steps mixed with audit and optional recovery detail | Lead with exact candidate checks, feature/stable release paths and manual acceptance; preserve quality-scale evidence in a navigable maintainer section |
| **Medium** | [Architecture](architecture.md) (~460 lines) and [Contributing](../CONTRIBUTING.md) | Possible duplicated toolchain, module inventory and workflow descriptions | Keep a clear system architecture, package boundaries and one canonical development/version process |
| **Low** | [Roadmap](roadmap.md), [Changelog](../CHANGELOG.md), [Assets](asset-provenance.md) | Potential stale PR-era feature descriptions or repeated provenance | Update future-work claims after verifying merges; retain historical changelog; link to authoritative JSON asset inventory |
| **Low** | [Examples](../examples/README.md), [test-area READMEs](../tests/README.md) | Navigation/overlap risk | Keep short ownership and discovery pointers; avoid copying whole testing procedures |

### High priority — Getting started

- [ ] Use the visible user path: HACS/manual install → add mosque → readiness screen → select PDF/CSV/URL → map → compare → **explicitly approve** → add card.
- [ ] Add a compact explanation of the PR #119 readiness screen, including timezone, today/tomorrow coverage, and missing required fields.
- [ ] Check the PR #120 details: show missing **field names and counts**, and correctly identify the shortcut for changing required fields/timezone.
- [ ] Keep basic setup fields, multiple-mosque configuration, reconfiguration and deletion warnings discoverable.
- [ ] Replace repeated importer restrictions, compatibility policies and deep troubleshooting with short summaries and links.
- [ ] Verify existing getting-started screenshots against the final editor and day/month navigation UI.

### High priority — Import and review

- [ ] Structure by tasks: supported PDF layouts, manual CSV, HTTPS URL, mapping, read-only comparison, approval/rejection, Ramadan, annual rollover and troubleshooting.
- [ ] Maintain one concise supported-PDF layout table with parser identifiers and user-relevant limits. Move lengthy Mosque A/B extraction measurements and synthetic fixture discussion to existing parser/testing/architecture references where appropriate.
- [ ] Document PR #119's **cross-year manual CSV** separately from standard annual/monthly/Ramadan imports: starts in the selected Gregorian year, spans at most 366 days across adjacent years, uses one source identity and rejects overlaps.
- [ ] Document PR #120's mapping suggestion: only previously approved **manual CSV** sources with matching full header set and timetable type; reordered columns may match, conflicting prior mappings must not be auto-selected; user must verify date column, prayer mappings and time format.
- [ ] Describe whole-source replacement and the PR #120 **removed-date warning** (count, first/last date and review of the comparison) without implying the new CSV merges records row by row.
- [ ] Document the annual URL rollover eligibility, publisher template with exactly one `{year}` token, editable generated URL, distinct validation errors and approval gate. Do not promise automatic discovery.
- [ ] State explicitly that unsupported cross-year PDF/URL formats and OCR are not silently accepted; preserve download protections, supported years, file bounds and storage/downgrade warnings.
- [ ] Keep Ramadan confirmation distinct from Hijri display and ordinary annual data.

### High priority — Dashboard

- [ ] Organise the settings reference by the actual editor sections: Dates & calendar; Prayer countdowns; Ramadan & night; Appearance; Timetable & information; Islamic history; Advanced settings.
- [ ] Explain Compact, Standard and Detailed in one concise comparison, with Yesterday/Today/Tomorrow behaviour and multiple-mosque selection.
- [ ] Combine toggles, dependencies, defaults, time formatting and background options into one consistently named reference rather than scattered descriptions.
- [ ] Preserve accurate distinctions for calculated Hijri dates, sunset-based day boundaries, night midpoint/final third and active Ramadan data.
- [ ] Keep monthly timetable, CSV export, source details and mobile/tablet/kiosk guidance user-focused.
- [ ] Move background attribution/hash maintenance, frontend implementation notes and obsolete YAML keys into appropriate **existing** maintainer references. Keep essential fallback/resource troubleshooting accessible.
- [ ] Audit images, captions and resource-loading tips against the released card.

### High priority — Automations and README

- [ ] Group Automations by user task: prayer reminders, media/Adhan blueprints, field-completeness alerts, coverage alerts, and prayer calendar.
- [ ] Ensure completeness alerts proposed by PR #119 are documented as distinct from coverage checks; describe sensor availability and attribute presence only when values exist (PR #120 correction).
- [ ] Keep one entity reference. Cross-link from Getting Started and Imports instead of reproducing sensor lists.
- [ ] Keep README concise: what the integration does, published-time accuracy warning, dashboard preview, install method, guides and contribution links.
- [ ] Verify the HACS *custom repository versus default catalogue* statement at implementation time; do not assume catalogue acceptance.
- [ ] Preserve shared installation/support excerpts so README and Getting Started cannot drift.

### Medium priority — Maintainer references

- [ ] Reduce repetition between `docs/testing.md`, `tests/README.md` and `tests/*/README.md`; preserve area ownership, exact commands, coverage and fixture expectations.
- [ ] Review the hard-coded test-module table and consider generating it from inventory tests. Do not weaken `tests/tooling/test_suite_inventory.py` or tests of CI ownership to reduce maintenance.
- [ ] Clarify docs-only CI behaviour, CodeQL targeting `main` (per PR #120 correction), disposable Container acceptance and physical-device limitations.
- [ ] Consolidate release CI command blocks and explain feature-release lifecycle, stable release publication, candidate versioning, exact-commit checks and manual HACS acceptance.
- [ ] Keep the internal Home Assistant Quality Scale audit qualified as **not** an official tier; keep optional HAOS backup/restore distinct from mandatory tests.
- [ ] Review architecture/module inventory and `CONTRIBUTING.md` for duplicated version commands and generated metadata instructions.

### Low priority — Governance and consistency

- [ ] Keep roadmap limited to *future work*. After PRs #119/#120 merge, check whether cross-year and alert/template items should move out of future-work sections.
- [ ] Preserve historical changelog versions and notes; only correct genuinely stale forward-looking descriptions.
- [ ] Use `docs/asset-provenance.json` and existing research sources as the authoritative inventories, with links rather than repeated data.
- [ ] Standardise Salah/Jamaat, Hijri/Gregorian, mosque naming/anonymisation, headings and screen-label capitalisation across guides.
- [ ] Identify repeated paragraphs about installation, sensor completeness, approval, Hijri display, Ramadan activation, PDF compatibility, diagnostics and support limitations; assign **one canonical owner** to each.

## Canonical document ownership

| Subject | Source of truth |
| --- | --- |
| Summary and installation entry | `README.md` |
| First-time user journey, setup and common issues | `docs/getting-started.md` |
| Supported sources, mappings, validation, comparison and approval | `docs/import_review.md` |
| Card/editor options, display and troubleshooting | `docs/dashboard.md` |
| Sensor/entity reference, automations, calendar and alerts | `docs/automations.md` |
| Integration modules and data lifecycle | `docs/architecture.md` |
| Test and compatibility process | `docs/testing.md` plus brief area-specific test READMEs |
| Release workflow, sign-off and quality audit | `docs/releasing.md` |
| Version source and contributor workflow | `versions.toml` and `CONTRIBUTING.md` |
| Licences and photo/fixture rights | `docs/asset-provenance.json` and `docs/asset-provenance.md` |
| Feature backlog | `docs/roadmap.md` |

## Codex implementation sequence

1. **Phase 0 — Rebaseline:** after both dependent PRs merge, check the current `main`, identify real duplicate passages and create a short *keep / simplify / move / link* inventory for each guide. Do not overwrite work merged since this review.
2. **Phase 1 — User guides:** implement Getting Started, Import and Review, Dashboard, Automations and README simplification. Keep changes small and reviewable; use the above checkboxes as acceptance criteria.
3. **Phase 2 — Maintainer guides:** simplify Testing, Releasing, Architecture and Contributing. Adjust existing test-area READMEs only if they genuinely duplicate or conflict.
4. **Phase 3 — Consistency:** audit heading anchors, relative links, captions, version/excerpt markers and cross-document terminology; optionally propose better automated checks in a **separate reviewed change** if scripts/tests would be affected.
5. **Review:** explain the sections removed/moved, retained safety constraints, new canonical links and tests/checks actually run. Leave PRs open; do not merge, delete branches, publish releases or tags without explicit authorisation.

## Validation and definition of done

- [ ] Each documented workflow matches the actual released/post-merge interface and implementation.
- [ ] A first-time user can follow installation → import/approve → dashboard without switching into architecture/testing material.
- [ ] Multiple mosques, Ramadan, required-field completeness alerts and cross-year replacement behaviour are accurately documented.
- [ ] Explicit approval and all strict parser/source restrictions remain unambiguous.
- [ ] Each repeated technical topic has a clearly assigned canonical home; remaining cross-references are short and accurate.
- [ ] Local Markdown file links, heading fragments, screen captures and shared-excerpt markers are verified.
- [ ] Run `python scripts/sync_documentation.py --check` and `python scripts/sync_versions.py --check`; verify the repository documentation-integrity workflow. If the approved implementation changes scripts or Python, add appropriate regression tests and perform Ruff checks.
- [ ] Review rendered GitHub Markdown and check for old references to `agents.md`; the root instruction filename is `AGENTS.md`.
- [ ] Summarise changed guides, validation evidence and any deferred improvements before requesting approval to merge.

**Out of scope:** implementing PR #119 or PR #120, changing runtime behavior, altering supported prayer calculations or creating feature releases. This file is the actionable documentation cleanup plan, not the product feature roadmap.
