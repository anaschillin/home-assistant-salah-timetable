# Roadmap

This page records **future work only**, not completed milestones or old pull request history. Priorities are proposals, not committed dates.

For features available in the current implementation, see the [README](../README.md#features)
and [setup guide](getting-started.md). In particular, prayer-completeness diagnostics,
monthly browsing/CSV export, guided annual URL rollover and automatic stable-release
publishing already exist. The follow-ups below describe their remaining limits;
their presence here does not mean those features still need to be built.

## Planned improvements

- **Upstream dependency advisories:** review current [dependency alerts](https://github.com/anaschillin/home-assistant-salah-timetable/security/dependabot) against the locked candidate environment and adopt supported upstream fixes under the [advisory policy](../SECURITY.md#dependency-advisories). The roadmap is not a live advisory inventory; do not override Home Assistant's exact requirements to clear an alert.
- **Home Assistant Integration Quality Scale:** address the [remaining Platinum gaps in the 54-rule audit](releasing.md#home-assistant-integration-quality-scale-internal-gap-audit): strict typing and HA-managed HTTP sessions with the current public-only DNS/redirect protections preserved. Review rule-specific evidence, the custom branding route and each exemption before claiming a tier.
- **Verified timetable coverage:** support additional annual, monthly and Ramadan publications only with reviewed examples and independent expected results; preserve strict date, format and HTTPS validation.
- **Prayer completeness follow-up:** consider optional event-driven alerts for missing required fields. The [diagnostic sensor and configurable required fields](automations.md#prayer-completeness) are implemented; the existing health blueprint checks date coverage and source review, not field completeness.
- **Monthly/export follow-up:** consider a native download fallback for Android WebViews that restrict browser Blob downloads. [Monthly browsing and approved-year CSV export](getting-started.md#browse-yesterday-and-the-monthly-timetable) are implemented; keep any fallback within authenticated Home Assistant APIs.
- **Import usability:** make setup, differences and error messages clearer without weakening explicit approval.
- **Release acceptance:** record candidate-specific manual HACS/Home Assistant results using the [acceptance checklist](releasing.md#manual-hacs-and-home-assistant-acceptance). [Stable publication after passing CI](releasing.md#automatic-stable-releases) is automated; full HAOS/Supervisor restoration remains an optional separate resilience exercise.
- **HACS catalogue:** complete the separate [default-catalogue submission and upstream review](releasing.md#publishing-to-the-hacs--home-assistant-marketplace-catalogue) after its prerequisites are met. Release automation and discovery metadata do not establish catalogue inclusion; custom-repository installation remains the documented route.

## Deferred or exploratory

- **Publication discovery:** guided rollover already accepts an explicitly supplied next-year URL. Automatic discovery would need configured publisher URL templates and independent tests; no publisher URLs are guessed.
- **Cross-year imports:** native support for one publication spanning December–January is not implemented. Imports remain limited to one declared Gregorian year; see [import limits](import_review.md#remaining-limits).
- **Additional integration translations and Arabic wording review:** on hold. The card already supports English/Arabic labels and RTL; Home Assistant setup/entity translations currently ship in English. Preserve identifiers and data behaviour; no target release date is assigned.
- **Special prayer events:** consider only events with verified publication dates.
- **Islamic history companion:** research only; resolve date authenticity, editorial scope and rights before considering a runtime dataset. See [source review](../research/islamic-history/islamic-history-source-audit.md).

Completed work belongs in the implementation and Git history, not this roadmap.
