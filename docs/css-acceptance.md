# CSS refactor acceptance (PR #82)

This checklist is for the **unmerged branch** `refactor/card-css-module-20261027`.
The feature is still integration version `0.9.3`; GitHub Actions passing does
not establish a successful installation on the maintainer's Home Assistant.

## Manual Home Assistant validation before merge

1. Back up the current `/config/custom_components/salah_timetable/` directory
   or test on a disposable Home Assistant installation.
2. Download the **branch** files from PR #82 (not the default `main` branch).
   For a complete trial installation, replace the integration directory with
   the branch copy. In particular, confirm these three files are together:
   `frontend/salah-timetable-card.js`, `frontend/card-styles.js`, and the
   existing `frontend/card-utils.js` and `frontend/card-i18n.js` dependencies.
   A normal HACS download of `main` **will not** install the unmerged PR.
3. Restart Home Assistant so the integration's static routes are registered.
   Confirm `/salah_timetable/card-styles.js?v=0.9.3` returns JavaScript
   (HTTP 200) in browser developer tools; no HTTP 404 or module-import errors.
4. The browser's prior `?v=0.9.3` resources may be cached. For this
   **branch test only**, change the dashboard's Salah Timetable JavaScript
   resource URL cache key to `?v=0.9.3-pr82`, or use a fresh private
   browsing session with cache disabled. Reload the dashboard or clear the
   Home Assistant mobile-app frontend cache. Avoid creating multiple
   duplicate resources. The module's own dependency imports remain pinned
   to `0.9.3`; inspect network requests to verify which bytes loaded.
5. On a real tablet and Android phone, compare the existing card and branch
   card in light/dark themes and compact/standard/detailed views. Check:
   - Both Next Salah and contextual Jamaat panels, including clock tick
     updates, emphasis, and published time labels.
   - 320–400 px mobile and tablet width changes: panel stacking, table
     horizontal scrolling, Ramadan grid, long mosque names and 200% text.
   - Arabic/right-to-left and bilingual prayer labels; keyboard focus and
     horizontal scrolling where a table overflows.
   - Selected day and mosque tabs, focus outline, Hijri month details,
     Ramadan entries, high-contrast and reduced-motion preferences.
6. Check Home Assistant browser console and network requests for
   `card-styles.js` import failures; capture screenshots of any differences.
   If styles do not load, restore the original integration files and resource
   URL, then restart.

## Automated evidence

- [PR #82](https://github.com/anaschillin/home-assistant-salah-timetable/pull/82)
  [Validate run 40594333792](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40594333792):
  7/7 jobs passed; 957 tests in each Python lane, 95.37% line coverage,
  plus real Chromium tests across sixteen width/language/bilingual combinations.
- [CodeQL 40594333630](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40594333630):
  passed.
- The test suite validates import availability, computed styles and layout,
  but does **not** yet compare rendered screenshot pixels to a golden baseline.

**Release status:** await maintainer's actual Home Assistant visual acceptance;
do not merge PR #82 until that review is complete. After merge, increment
the integration version through the central version-sync workflow for HACS
cache invalidation.
