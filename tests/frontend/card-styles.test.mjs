/** Style regressions complement the real Chromium responsive-layout checks. */
import test from "node:test";
import assert from "node:assert/strict";
import {CARD_CSS, EDITOR_CSS} from "../../custom_components/salah_timetable/frontend/card-styles.js";

test("theme, accessibility and responsive styles remain bundled", () => {
  for (const token of [
    ":host", "ha-card", "--primary-color", "--secondary-background-color",
    ".date-tab,.mosque-tab", ".panel[data-panel=\"salah\"]",
    ".next-prayer", ".scroll-help", ".sr-only", "unicode-bidi: isolate",
    "@container(max-width:26rem)", "@container(max-width:28rem)",
    "@media(max-width:420px)", "@media(prefers-contrast:more)",
    "@media(prefers-reduced-transparency:reduce)",
    "@media(prefers-reduced-motion:no-preference)",
  ]) assert.ok(CARD_CSS.includes(token), `Missing CSS safeguard: ${token}`);
});

test("shared tab controls retain active and keyboard-focus treatments", () => {
  assert.match(CARD_CSS, /\.date-tab\[aria-pressed="true"\],\.mosque-tab\[aria-pressed="true"\]/);
  assert.match(CARD_CSS, /\.date-tab:focus-visible,\.mosque-tab:focus-visible/);
  assert.match(CARD_CSS, /\.date-tab,\.mosque-tab\s*\{/);
});

test("graphical editor retains focus, layout, theme and narrow-screen styles", () => {
  for (const token of [":host", ".form", ".title-field input", ".title-field input:focus", "--primary-color", "--secondary-text-color", "@media(max-width: 420px)"]) {
    assert.ok(EDITOR_CSS.includes(token), `Missing editor style: ${token}`);
  }
});

test("later responsive and modern panel overrides remain ordered", () => {
  assert.ok(CARD_CSS.indexOf("@container(max-width:26rem)") < CARD_CSS.indexOf("@container(max-width:28rem)"));
  assert.ok(CARD_CSS.indexOf("/* Modern dashboard presentation") < CARD_CSS.indexOf("@container(max-width:28rem)"));
  assert.ok(CARD_CSS.includes(".panel .count"));
});
