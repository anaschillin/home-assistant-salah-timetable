# Frontend visual regression checks

The Chromium smoke suite exercises 16 combinations: widths 320, 360, 400 and
900 px; English and Arabic; single-language and bilingual prayer labels.
It checks accessible semantics, overflow, RTL, calendar text, the editor,
keyboard focus, styles, and theme variables before capturing each screenshot.

On a **pull request**, the Validate workflow:

1. Runs the candidate card in Chromium and captures 16 PNG screenshots.
2. Checks out the **current base branch HEAD** in a separate directory.
   The workflow logs the resolved baseline commit SHA for reproducibility.
3. Runs the same browser smoke test on the base branch on the same CI runner,
   ensuring the same installed Chrome and system fonts.
4. Compares each candidate/base screenshot with
   `node scripts/compare_screenshots.mjs BASE_DIR CURRENT_DIR`.
   Dimensions must match. A pixel counts as changed only if one RGBA
   channel differs by more than 16 (out of 255); greater than **0.5%**
   changed pixels in any one fixture fails the frontend job.
5. On failure, uploads the candidate and baseline PNGs in a
   `frontend-visual-diff-<PR number>` artifact for human review. Approved
   visual redesigns upload the same artifact even when comparison succeeds,
   so reviewers can inspect the before/after evidence.

PNG files are local CI evidence, not source-controlled brand or mosque
fixtures. The decoder is dependency-free and accepts only bounded,
8-bit RGB/RGBA, noninterlaced PNGs from the local Chromium capture.

For deliberate visual redesigns (including changed card heights), inspect
the screenshot artifact, document the expected changes in the PR and have a
repository maintainer apply the `visual-change-approved` PR label. **Do not
apply this label to ordinary CSS/behavior fixes or unrelated feature PRs.**
The comparer still captures and decodes all 16 current/base screenshots,
checks their presence and filenames, prints dimension/pixel changes and emits
a GitHub Actions notice. Only an explicitly labelled PR may accept differences
beyond 0.5% or intentionally changed dimensions. Without that label, the
strict 0.5% threshold and dimension checks continue to fail unexpected changes.

The label represents manual design approval, **not proof of accessibility or
real-device acceptance**. Chromium overflow/RTL tests, frontend unit tests and
Home Assistant acceptance still run and must pass. The label only approves
the screenshot delta from the PR base. After merging the redesigned card, its
images become the normal baseline for later PRs; remove or avoid the approval
label on new unrelated changes. This does not raise the tolerance or disable
comparisons. If the base branch changes while a review is in progress, rerun
CI and record the resolved base SHA. Pushes to `main` still run browser smoke
tests but cannot compare against a pull-request base branch.

Run locally:

```bash
BROWSER_SCREENSHOT_DIR=/tmp/salah-current npm run test:browser
# Run the same command with a second checkout and a different output directory.
node scripts/compare_screenshots.mjs /tmp/salah-base /tmp/salah-current
```

The images use synthetic fixture data. Physical Home Assistant acceptance
on a phone/tablet, as described in [CSS acceptance](dashboard.md),
remains a separate release gate.
