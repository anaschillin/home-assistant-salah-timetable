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
  for (const token of [":host", ".form", ".setting select:focus-visible", "--primary-color", "--secondary-text-color", "@media(max-width: 420px)"]) {
    assert.ok(EDITOR_CSS.includes(token), `Missing editor style: ${token}`);
  }
});

test("later responsive and modern panel overrides remain ordered", () => {
  assert.ok(CARD_CSS.indexOf("@container(max-width:26rem)") < CARD_CSS.indexOf("@container(max-width:28rem)"));
  assert.ok(CARD_CSS.indexOf("/* Modern dashboard presentation") < CARD_CSS.indexOf("@container(max-width:28rem)"));
  assert.ok(CARD_CSS.includes(".panel .count"));
});

test("panel editor keeps native card proportions without custom nested scrolling", () => {
  const start = CARD_CSS.indexOf("/* Home Assistant's Panel editor owns");
  const end = CARD_CSS.indexOf(".source-summary {", start);
  assert.ok(start >= 0 && end > start);
  const edit = CARD_CSS.slice(start, end);
  for (const banned of ["max-height:", "overflow-y:", "scrollbar-gutter:", "transform:", "zoom:", "grid-template-columns:", "font-size:", "padding:"]) {
    assert.ok(!edit.includes(banned), `Unexpected edit-only style: ${banned}`);
  }
  assert.ok(CARD_CSS.includes(":host([dashboard-editing]) ha-card.has-mosque-background"));
});

test("dashboard edit/preview removes only the full-viewport photo minimum", () => {
  const editOnly = CARD_CSS.match(/:host\(\[dashboard-editing\]\) ha-card\.has-mosque-background\s*\{([^}]+)\}/);
  assert.ok(editOnly, "Preview-only height override is missing");
  assert.match(editOnly[1], /min-height:\s*0\s*;/);
  const defaultHeight = CARD_CSS.match(/(?<!\])ha-card\.has-mosque-background\s*\{([^}]+)\}/);
  assert.match(defaultHeight[1], /min-height:\s*var\(--salah-viewport-card-height,/);
});

test("mosque photo fills the measured visible viewport but can grow beyond it", () => {
  const rule = CARD_CSS.match(/ha-card\.has-mosque-background\s*\{([^}]+)\}/);
  assert.ok(rule, "Missing full-canvas background rule");
  assert.match(rule[1], /min-height:\s*var\(--salah-viewport-card-height,\s*calc\(100dvh/);
  assert.doesNotMatch(rule[1], /max-height:|height:\s*\d+dvh/);
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*min-height:\s*var\(--salah-viewport-card-height/);
  assert.match(CARD_CSS, /ha-card\.kiosk\s*\{[^}]*min-height:\s*0/);
  assert.match(CARD_CSS, /ha-card\.kiosk:fullscreen\s*\{[^}]*min-height:\s*100dvh/);
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
  // Only match unscoped card declarations. Edit-only :host(...) ha-card
  // overrides may follow them without adding an unwanted drop shadow.
  const cardRules = [...CARD_CSS.matchAll(/(?:^|\n)ha-card\s*\{([^}]+)\}/g)];
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

test("monthly button shares the mosque name row without altering the default header", () => {
  assert.match(CARD_CSS, /\.header h2\s*\{[^}]*grid-column:\s*1 \/ -1/);
  assert.match(CARD_CSS, /\.summary-shell \.header:has\(\.card-action-strip\) h2\s*\{[^}]*grid-column:\s*1;\s*grid-row:\s*1/);
  assert.match(CARD_CSS, /@container\(max-width:23rem\)\s*\{\s*\.header\s*\{\s*grid-template-columns:\s*minmax\(0,1fr\)/);
  assert.match(CARD_CSS, /\.header \.gregorian\s*\{\s*text-align:\s*start/);
  assert.match(CARD_CSS, /\.card-action-strip\s*\{[^}]*grid-column:\s*2;\s*grid-row:\s*1/);
  assert.match(CARD_CSS, /\.header \.gregorian\s*\{[^}]*grid-column:\s*2;\s*grid-row:\s*2/);
  assert.match(CARD_CSS, /\.card-action-strip ha-icon\s*\{[^}]*width:\s*1em;[^}]*height:\s*1em/);
  assert.match(CARD_CSS, /\.card-action-strip button span\s*\{[^}]*font-size:\s*inherit/);
  assert.match(CARD_CSS, /@container\(max-width:33rem\)\s*\{\s*\.card-action-strip button span\s*\{\s*display:\s*none/);
});

test("Compact More menu is an overlay and does not reflow the summary header", () => {
  assert.match(CARD_CSS, /\.card-actions-menu\s*\{[^}]*position:\s*absolute/);
  assert.match(CARD_CSS, /\.card-actions-menu \.card-menu-items\s*\{[^}]*position:\s*absolute/);
  assert.match(CARD_CSS, /\.summary-shell:has\(\.card-actions-menu\[open\]\)\s*\{[^}]*overflow:\s*visible/);
  assert.match(CARD_CSS, /\.summary-shell \.header:has\(\.card-actions-menu\[open\]\)\s*\{[^}]*z-index:/);
});

test("kiosk 3.0 layout preserves full-bleed photo and distance-readable contrast", () => {
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*grid-template-rows:\s*auto auto auto/);
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*align-content:\s*safe center/);
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*justify-items:\s*center/);
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/);
  assert.match(CARD_CSS, /\.content\.kiosk > \.summary-shell,[\s\S]*?\.content\.kiosk > \.kiosk-footer,[\s\S]*?\.content\.kiosk > \.monthly-shell\s*\{[^}]*max-width:\s*1600px/);
  assert.match(CARD_CSS, /ha-card\.kiosk:fullscreen \.content\.kiosk\s*\{[^}]*min-height:\s*100dvh/);
  assert.match(CARD_CSS, /\.content\.kiosk\s*\{[^}]*min-height:\s*var\(--salah-viewport-card-height/);
  assert.match(CARD_CSS, /:host\(\[dashboard-editing\]\) \.content\.kiosk\s*\{[^}]*grid-template-rows:\s*auto/);
  assert.match(CARD_CSS, /:host\(\[dashboard-editing\]\) \.content\.kiosk\s*\{[^}]*align-content:\s*start/);
  assert.match(CARD_CSS, /ha-card\.kiosk\.has-mosque-background::before,[\s\S]*?ha-card\.kiosk\.has-mosque-background::after\s*\{[^}]*width:\s*100%;[^}]*height:\s*100%;[^}]*background-size:\s*cover/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell\s*\{[^}]*min-height:\s*clamp\(270px, 33dvh, 350px\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.header\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(0, 1fr\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.panels\s*\{[^}]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-panel\[data-panel="jamaat"\] \.count\s*\{[^}]*color:\s*var\(--primary-text-color\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-strip\s*\{[^}]*grid-template-columns:\s*repeat\(5, minmax\(0, 1fr\)\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-tile\s*\{[^}]*97%, transparent\)[^}]*backdrop-filter:\s*blur\(18px\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-tile\.is-next\s*\{[^}]*background:\s*color-mix\(in srgb, var\(--primary-color\) 74%, #10202b\)/);

  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-tile\.is-next-jamaat\s*\{[^}]*box-shadow:\s*inset 0 0 0 2px/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-next-day\s*\{[^}]*border:\s*1px solid/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-panel\[data-panel="jamaat"\] \.count\s*\{[^}]*font-size:\s*clamp\(2rem, min\(5\.6cqi, 9\.2dvh\), 6\.2rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-panel\[data-panel="jamaat"\] \.event\s*\{[^}]*font-size:\s*clamp\(1\.5rem, calc\(var\(--kiosk-u\) \* 4\.7\), 3\.5rem\)/);

  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-tile\.is-past\s*\{[^}]*opacity:/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-tile-label\s*\{[^}]*font-size:\s*clamp\(1rem, 1\.13cqi, 1\.125rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-footer\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(0, 1fr\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-footer-info\s*\{[^}]*grid-column:\s*1/);

  assert.match(CARD_CSS, /ha-card\.kiosk\s*\{[^}]*min-height:\s*0/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-panel \.count\s*\{[^}]*font-size:\s*clamp\(2rem, min\(5\.6cqi, 9\.2dvh\), 6\.2rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-panel\[data-panel="jamaat"\] \.count span\s*\{[^}]*color:\s*inherit/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell \.prayer-time \.label\s*\{[^}]*font-size:\s*clamp\(1rem, 1\.13cqi, 1\.125rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-clock-label\s*\{[^}]*font-size:\s*clamp\(1rem, 1\.15cqi, 1\.125rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-footer-info \.background-credit\s*\{[^}]*max-width:\s*100%/);

  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-footer-info \.background-credit\s*\{[^}]*font-size:\s*clamp\(\.73rem, \.9cqi, \.87rem\)/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-day-tabs \.date-tab:not\(\[aria-pressed="true"\]\)\s*\{[^}]*opacity:\s*\.95/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-footer \.kiosk-toolbar\s*\{[^}]*grid-column:\s*3/);
  assert.match(CARD_CSS, /\.content\.kiosk \.kiosk-clock-value\s*\{[^}]*font-variant-numeric:\s*tabular-nums/);
  assert.match(CARD_CSS, /@container\(max-width:60rem\)/);
  assert.match(CARD_CSS, /@container\(max-width:40rem\)/);
  assert.match(CARD_CSS, /@container\(max-width:24rem\)/);
  assert.match(CARD_CSS, /prefers-reduced-transparency:\s*reduce/);
});

test("kiosk fullscreen is a tiny overlay inside summary, not a footer button", () => {
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell\s*\{[^}]*position:\s*relative/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell > \.kiosk-fullscreen\s*\{[^}]*position:\s*absolute;[^}]*top:\s*12px;[^}]*right:\s*12px/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell > \.kiosk-fullscreen\s*\{[^}]*width:\s*30px;[^}]*height:\s*30px/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell > \.kiosk-fullscreen ha-icon\s*\{[^}]*--mdc-icon-size:\s*17px/);
  assert.match(CARD_CSS, /\.content\.kiosk \.summary-shell > \.kiosk-fullscreen:focus-visible\s*\{[^}]*outline:/);
  assert.doesNotMatch(CARD_CSS, /\.content\.kiosk \.kiosk-footer \.kiosk-fullscreen\s*\{/);
});
