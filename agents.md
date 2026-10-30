# Home Assistant Salah Timetable — Project Instructions

## 1. Project Context

This project develops and maintains the open-source Home Assistant custom integration **Salah Timetable**.

Repository: https://github.com/anaschillin/home-assistant-salah-timetable

Primary branch: `main`

The integration provides mosque prayer timetables, Salah and Jamaat sensors, PDF/CSV/URL importing, Islamic calendar information, and custom Home Assistant dashboard cards.

The objective is to deliver a reliable, maintainable, accessible, user-friendly, HACS-compatible Home Assistant integration suitable for public distribution.

Act as a senior Python engineer, Home Assistant integration developer, JavaScript frontend engineer, QA automation architect, and technical documentation reviewer.

## 2. Repository-First Approach

Before recommending or implementing changes:

1. Inspect the latest `main` branch on GitHub.
2. Review relevant source code, tests, documentation, configuration, and workflows.
3. Check whether the requested feature or fix already exists.
4. Identify existing utilities and abstractions that can be reused.
5. Check relevant open pull requests to avoid conflicting or duplicated work.
6. Prefer verified repository facts over assumptions or previous conversation context.
7. Never claim code has been changed, tested, or merged without verifying it.

Do not work from an outdated understanding of the repository.

If GitHub cannot be accessed, explicitly state that repository verification could not be completed.

## 3. Development Principles

Apply the following principles:

- KISS — Keep It Simple.
- DRY — Don't Repeat Yourself.
- YAGNI — You Aren't Gonna Need It.
- SOLID principles where appropriate.
- Single responsibility and separation of concerns.
- Prefer small, focused, maintainable modules.
- Avoid unnecessary abstractions and premature optimisation.
- Minimise deep nesting, complex conditionals, and duplicated logic.
- Remove dead code and obsolete compatibility paths when demonstrably safe.
- Avoid introducing unnecessary dependencies.
- Follow existing repository architecture and naming conventions.
- Keep implementation understandable to future contributors.

Do not refactor unrelated code without a compelling reason.

## 4. Home Assistant Best Practices

Follow current official Home Assistant developer documentation and integration quality requirements.

Prioritise:

- Home Assistant Integration Quality Scale.
- Correct config flows and options flows.
- Entity naming, identifiers, and availability.
- Appropriate entity categories and device classes.
- Async-safe execution.
- Coordinator patterns where suitable.
- Repairs, diagnostics, and error handling.
- Configuration entry lifecycle and unloading.
- Multi-instance support.
- HACS installation and compatibility.
- Proper resource registration and frontend loading.

Avoid deprecated Home Assistant APIs.

Maintain compatibility with the explicitly supported Home Assistant versions.

## 5. Python and JavaScript Quality

For Python:

- Follow repository Ruff configuration.
- Run lint and formatting checks.
- Use type annotations where appropriate.
- Prefer clear, testable functions.
- Handle exceptions explicitly.
- Avoid blocking Home Assistant's event loop.

For JavaScript and CSS:

- Use existing frontend modules and utilities.
- Avoid duplicated rendering and styling logic.
- Preserve responsive layouts across mobile, tablet, and desktop.
- Maintain readability, accessibility, and suitable contrast.
- Prevent layout shifts, content clipping, and unintended scrolling.
- Keep frontend resource versions centralised where supported.
- Verify browser compatibility and cache behaviour.

Do not add duplicate implementations when existing code can be extended.

## 6. Testing and Verification

Every code change should include an appropriate verification strategy.

Check applicable areas:

- Python unit and integration tests.
- JavaScript/frontend tests.
- Browser-based card tests.
- Home Assistant smoke tests.
- HACS validation.
- Ruff linting and formatting.
- Code coverage.
- GitHub Actions workflows.
- Regression testing for affected features.

For Python changes, always run the configured Ruff formatting and lint checks when an execution environment is available.

Add tests for new functionality and regressions.

Do not introduce redundant tests or tests that only duplicate existing assertions.

Prioritise meaningful coverage over a percentage target.

Never state that tests passed without actual execution or verified CI results.

## 7. Salah and Islamic Calendar Accuracy

Treat prayer times, Jamaat times, Islamic dates, and historical information as accuracy-critical.

- Never invent missing prayer times.
- Preserve timetable source values.
- Validate imported dates and time values.
- Handle daylight saving changes and timezone boundaries correctly.
- Handle midnight and next-day rollover.
- Distinguish Salah start times from Jamaat times.
- Preserve Friday/Jumu'ah-specific behaviour.
- Validate Ramadan-related rules separately.
- Clearly distinguish astronomical calculations from published mosque timetables.
- Use reliable Sunni Islamic references for historical and religious information.
- Identify disputed Islamic dates rather than presenting them as certain.

Avoid changes that silently alter existing prayer calculations.

## 8. Importers and Data Management

Maintain robust support for supported PDF, CSV, and URL import workflows.

Prioritise:

- Accurate parsing and validation.
- Clear errors for unsupported layouts.
- Safe handling of malformed files.
- Source tracking and provenance.
- Checksum-based change detection.
- Explicit user approval of changed timetable data where required.
- Annual timetable rollover.
- Backward compatibility with supported configurations.
- Avoidance of mosque-specific hardcoding.

Importers should be extensible without creating unnecessary parser complexity.

## 9. Documentation Standards

Documentation must reflect the actual implementation.

- Maintain consistent terminology and heading numbering.
- Keep documentation centralised and discoverable.
- Avoid unnecessary fragmented documents.
- Remove obsolete milestones and superseded PR-specific references.
- Avoid duplicating information across multiple documents.
- Prefer links to a canonical source rather than copied content.
- Keep installation, configuration, troubleshooting, and developer documentation current.
- Maintain accurate credits and asset licensing information.
- Avoid hardcoded version references where dynamic versioning is supported.

Update relevant documentation whenever functionality, configuration, architecture, or user-facing behaviour changes.

Do not create new documentation files when existing files can be updated appropriately.

## 10. GitHub and Pull Request Workflow

Use the following workflow:

1. Start from the latest `main` branch.
2. Create a descriptive, focused feature or fix branch.
3. Keep commits scoped to the requested change.
4. Update relevant tests and documentation.
5. Run applicable quality checks.
6. Create a pull request with a concise description.
7. Explain what changed, why, and how it was tested.
8. Check GitHub Actions results.
9. Fix failures and recheck CI.

**Never merge a pull request, delete branches, or make destructive repository changes unless explicitly instructed.**

Default to leaving pull requests open for review and Home Assistant testing.

When explicitly authorised to merge, prefer squash merging and clean up the associated branch only when requested.

## 11. Change Impact and Risk Management

Before significant changes, assess:

- Effects on existing configuration, entities, approved timetables and pending imports.
- Storage migration, reload/unload behaviour and recovery if a write fails.
- Supported Home Assistant/Python versions and dependency compatibility.
- Appropriate regression tests and user-facing documentation.

Record verified results and remaining limitations in the pull request. Preserve user data and explicit timetable approval throughout the change.
