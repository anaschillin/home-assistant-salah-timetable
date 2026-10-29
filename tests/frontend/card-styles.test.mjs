/** Style regressions complement the real Chromium responsive-layout checks. */
import test from "node:test";
import assert from "node:assert/strict";
import {CARD_CSS, EDITOR_CSS} from "../../custom_components/salah_timetable/frontend/card-styles.js";

test("theme, accessibility and responsive styles remain bundled", () => {
  for (const token of [
    ":host", "ha-card", "--primary-color", "--secondary-background-color",
    ".date-tab", ".panel[data-panel=\"salah\"]",
    ".next-prayer", ".scroll-help", ".sr-only", "unicode-bidi: isolate",
    "@container(max-width:26rem)", "@container(max-width:28rem)",
    "@media(max-width:420px)", "@media(prefers-contrast:more)",
    "@media(prefers-reduced-transparency:reduce)",
    "@media(prefers-reduced-motion:no-preference)",
  ]) assert.ok(CARD_CSS.includes(token), `Missing CSS safeguard: ${token}`);
});

test("day navigation retains active and keyboard-focus treatments without obsolete mosque tabs", () => {
  assert.match(CARD_CSS, /\.date-tab\[aria-pressed="true"\]/);
  assert.match(CARD_CSS, /\.date-tab:focus-visible/);
  assert.match(CARD_CSS, /\.date-tab\s*\{/);
  assert.doesNotMatch(CARD_CSS, /\.mosque-tabs?\b/);
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

test("the mosque photograph covers the viewport below short day views", () => {
  const rule = CARD_CSS.match(/ha-card\.has-mosque-background\s*\{([^}]+)\}/);
  assert.ok(rule, "Missing full-canvas background rule");
  assert.match(rule[1], /min-height:\s*calc\(100vh - var\(--header-height, 0px\)\)/);
  assert.match(rule[1], /min-height:\s*calc\(100dvh - var\(--header-height, 0px\)\)/);
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*overflow:\s*hidden/);
  assert.doesNotMatch(CARD_CSS, /\.summary-shell\s*\{[^}]*min-height:\s*100dvh/);
});

test("background photo is clipped and its frame is independent of card height", () => {
  const imageLayer = CARD_CSS.match(/ha-card\.has-mosque-background::before\s*\{([^}]+)\}/);
  assert.ok(imageLayer, "Missing isolated image layer");
  assert.match(imageLayer[1], /height:\s*max\(calc\(100% - 2px\),var\(--mosque-photo-frame-height,100%\)\)/);
  assert.match(imageLayer[1], /width:\s*var\(--mosque-photo-frame-width,calc\(100% - 2px\)\)/);
  assert.match(imageLayer[1], /transform:\s*translateX\(-50%\)/);
  assert.match(imageLayer[1], /background-origin:\s*padding-box\s*;/);
  assert.match(imageLayer[1], /background-clip:\s*padding-box\s*;/);
  assert.match(imageLayer[1], /background-image:\s*var\(--mosque-background-image\)/);
  assert.doesNotMatch(CARD_CSS, /--mosque-overlay/);
  const blurredRim = CARD_CSS.match(/ha-card\.has-mosque-background::after\s*\{([^}]+)\}/);
  assert.ok(blurredRim, "Missing blurred photo rim");
  assert.match(blurredRim[1], /height:\s*max\(calc\(100% - 2px\),var\(--mosque-photo-frame-height,100%\)\)/);
  assert.match(blurredRim[1], /width:\s*var\(--mosque-photo-frame-width,calc\(100% - 2px\)\)/);
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*overflow:\s*hidden\s*;/);
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*border-radius:\s*var\(--ha-card-border-radius/);
});

test("full-canvas mosque background and centered glass content retain accessible fallback", () => {
  assert.match(CARD_CSS, /ha-card\s*\{[^}]*max-width:\s*none/);
  assert.match(CARD_CSS, /\.content\s*\{[^}]*max-width:\s*1160px/);
  assert.match(CARD_CSS, /\.content\s*\{[^}]*margin-inline:\s*auto/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{[^}]*filter:\s*blur\(14px\)/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{[^}]*mask-image:\s*radial-gradient/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background \.content\s*\{[^}]*backdrop-filter:\s*none/);
  assert.match(CARD_CSS, /prefers-reduced-transparency:\s*reduce/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{\s*display:\s*none/);
  assert.match(CARD_CSS, /\.header \.month-description\s*\{[^}]*grid-column:\s*1 \/ -1/);
  assert.match(CARD_CSS, /\.header\s*\{[^}]*display:\s*grid/);
  assert.doesNotMatch(CARD_CSS, /\.month-summary\s*\{/);
});


test("outer Home Assistant card has no drop shadow while both glass cards retain depth", () => {
  const cardRules = [...CARD_CSS.matchAll(/ha-card\s*\{([^}]+)\}/g)];
  assert.ok(cardRules.length >= 2);
  assert.ok(cardRules.slice(-2).every(match => /box-shadow:\s*none\s*;/.test(match[1])));
  assert.doesNotMatch(CARD_CSS, /ha-card\s*\{[^}]*box-shadow:\s*0\s+\d+px/);
  assert.match(CARD_CSS, /\.summary-shell,\s*\.timetable-shell\s*\{[^}]*box-shadow:/);
  assert.match(CARD_CSS, /ha-card\.has-mosque-background::after\s*\{[^}]*filter:\s*blur\(14px\)/);
});

test("summary and timetable share one CSS-first liquid-glass material", () => {
  const shared = CARD_CSS.match(/\.summary-shell,\s*\.timetable-shell\s*\{([^}]+)\}/);
  assert.ok(shared, "Both panels must share the same glass surface rule");
  for (const pattern of [
    /border-radius:\s*18px/, /linear-gradient\(135deg/,
    /backdrop-filter:\s*blur\(20px\) saturate\(115%\)/,
    /box-shadow:/, /ha-card-background/
  ]) assert.match(shared[1], pattern);
  assert.match(CARD_CSS, /\.summary-shell::before,\s*\.timetable-shell::before\s*\{/);
  assert.match(CARD_CSS, /\.summary-shell > \*,\s*\.timetable-shell > \*\s*\{/);
  assert.match(CARD_CSS, /\.timetable-shell thead,\s*\.timetable-shell \.date-tabs\s*\{/);
  assert.match(CARD_CSS, /@supports not \(backdrop-filter: blur\(1px\)\)/);
  assert.match(CARD_CSS, /@media \(prefers-contrast: more\), \(prefers-reduced-transparency: reduce\)/);
  assert.match(CARD_CSS, /\.summary-shell \.panel\.prayer-panel,\s*\.summary-shell \.panel\.prayer-panel\[data-panel="salah"\]\s*\{[^}]*background:\s*transparent/);
  assert.match(CARD_CSS, /@container\(max-width:21rem\)\s*\{\s*\.summary-shell \.panels\s*\{\s*grid-template-columns:\s*1fr/);
});

test("glass readability uses the same high-contrast substrate without an extra timetable tint", () => {
  const shared = CARD_CSS.match(/\.summary-shell,\s*\.timetable-shell\s*\{([^}]+)\}/);
  assert.ok(shared);
  assert.equal((shared[1].match(/ha-card-background[^\n]*\) 84%,transparent/g) || []).length, 2);
  assert.equal((shared[1].match(/ha-card-background[^\n]*\) 88%,transparent/g) || []).length, 1);
  assert.doesNotMatch(shared[1], /ha-card-background[^\n]*\) 9[25]%,transparent/,
    "Do not return to the overly dark glass opacity");
  assert.doesNotMatch(shared[1], /secondary-background-color\) (?:59|70|72)%,transparent/);
  assert.match(shared[1], /color:\s*var\(--primary-text-color\)/);
  const table = CARD_CSS.match(/\.timetable-shell thead,\s*\.timetable-shell \.date-tabs,\s*\.timetable-shell \.table-scroll\s*\{([^}]+)\}/);
  assert.ok(table, "Timetable header and navigation must not add their own glass layer");
  assert.match(table[1], /background:\s*transparent/);
  assert.match(CARD_CSS, /\.summary-shell \.date,\s*\.summary-shell \.month-description/);
});
