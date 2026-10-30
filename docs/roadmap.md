# Roadmap

This page records **future work only**, not completed milestones or old pull request history. Priorities are proposals, not committed dates.

## Planned improvements

- **Home Assistant Integration Quality Scale:** address the [remaining Platinum gaps in the 54-rule audit](releasing.md#home-assistant-integration-quality-scale-internal-gap-audit): strict typing and HA-managed HTTP sessions with the current public-only DNS/redirect protections preserved. Review rule-specific evidence, the custom branding route and each exemption before claiming a tier.
- **Verified timetable coverage:** support additional annual, monthly and Ramadan publications only with reviewed examples and independent expected results; preserve strict date, format and HTTPS validation.
- **Import usability:** make setup, differences and error messages clearer without weakening explicit approval.
- **Release readiness:** record results of relevant HACS/HAOS testing for a tagged release; full HAOS/Supervisor restoration remains an optional separate resilience exercise.
- **HACS catalogue:** consider default-catalogue submission once release acceptance and submission requirements are met; custom-repository installation remains supported.

## Deferred or exploratory

- **Further integration translations and reviewed Arabic wording:** on hold. Preserve current identifiers and data behaviour; no target release date is assigned.
- **Night calculations:** investigate clearly labelled calculated midnight/last-third values, separate from mosque publications.
- **Mosque display mode:** explore wall/tablet presentation and user-controlled announcements.
- **Special prayer events:** consider only events with verified publication dates.
- **Islamic history companion:** research only; resolve date authenticity, editorial scope and rights before considering a runtime dataset. See [source review](../research/islamic-history/islamic-history-source-audit.md).

Completed work belongs in the implementation and Git history, not this roadmap.
