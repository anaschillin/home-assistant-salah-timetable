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

test("mosque background and tint are clipped at the rounded card border", () => {
  const rules = CARD_CSS.match(/ha-card\.has-mosque-background\s*\{([^}]+)\}/);
  assert.ok(rules, "Missing photo backdrop style");
  assert.match(rules[1], /background-origin:\s*padding-box\s*;/);
  assert.match(rules[1], /background-clip:\s*padding-box\s*;/);
  assert.match(rules[1], /background-image:\s*linear-gradient\(var\(--mosque-overlay\)/);
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*overflow:\s*hidden\s*;/);
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*border-radius:\s*var\(--ha-card-border-radius/);
});

test("full-canvas mosque background and centered glass content retain accessible fallback", () => {
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*max-width:\s*none/);
  assert.match(CARD_CSS, /\.content\s*\{[^}]*max-width:\s*1160px/);
  assert.match(CARD_CSS, /\.content\s*\{[^}]*margin-inline:\s*auto/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{[^}]*filter:\s*blur\(14px\)/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{[^}]*mask-image:\s*radial-gradient/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background \.content\s*\{[^}]*backdrop-filter:\s*blur\(1px\)/);
  assert.match(CARD_CSS, /prefers-reduced-transparency:\s*reduce/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{\s*display:\s*none/);
  assert.match(CARD_CSS, /\.header \.month-description\s*\{[^}]*grid-column:\s*1 \/ -1/);
  assert.match(CARD_CSS, /\.header\s*\{[^}]*display:\s*grid/);
  assert.doesNotMatch(CARD_CSS, /\.month-summary\s*\{/);
});


test("one stronger glass surface gives Salah and Jamaat identical panel formatting", () => {
  assert.match(CARD_CSS, /\.summary-shell\s*\{[^}]*border-radius:\s*18px/);
  assert.match(CARD_CSS, /\.summary-shell\s*\{[^}]*secondary-background-color\) 94%,transparent/);
  assert.match(CARD_CSS, /\.summary-shell\s*\{[^}]*backdrop-filter:\s*blur\(18px\) saturate\(115%\)/);
  assert.match(CARD_CSS, /\.summary-shell\s*\{[^}]*margin-bottom:\s*16px/);
  // One shared selector must override the old Salah-only tint.
  assert.match(CARD_CSS, /\.summary-shell \.panel\.prayer-panel,\s*\.summary-shell \.panel\.prayer-panel\[data-panel="salah"\]\s*\{[^}]*background:\s*transparent/);
  assert.match(CARD_CSS, /\.summary-shell \.panel\.prayer-panel,\s*\.summary-shell \.panel\.prayer-panel\[data-panel="salah"\]\s*\{[^}]*border:\s*0/);
  assert.match(CARD_CSS, /\.summary-shell \.prayer-panel \+ \.prayer-panel\s*\{[^}]*border-inline-start/);
  assert.match(CARD_CSS, /@container\(max-width:21rem\)\s*\{\s*\.summary-shell \.panels\s*\{\s*grid-template-columns:\s*1fr/);
  assert.match(CARD_CSS, /@media \(prefers-contrast: more\), \(prefers-reduced-transparency: reduce\)/);
});
