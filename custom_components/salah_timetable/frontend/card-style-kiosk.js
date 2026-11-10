/** Ordered Salah Timetable styles: kiosk section. */
export const KIOSK_CSS = `/* Kiosk is strictly opt-in. Responsive sizing avoids clipping in phone WebViews. */
ha-card.kiosk {
  /* The content owns the measured viewport minimum. A second outer
     min-height can add a scrollable sliver below the Lovelace view. */
  min-height: 0;
  overflow: hidden;
}
ha-card.kiosk:fullscreen {
  min-height: 100dvh;
  height: 100dvh;
  overflow: auto;
  background: var(--ha-card-background,var(--card-background-color));
}
.content.kiosk {
  padding: clamp(12px, 2.5cqi, 34px);
}
.content.kiosk .summary-shell,
.content.kiosk .timetable-shell {
  max-width: 1400px;
  margin-inline: auto;
}
.content.kiosk .header h2 {
  font-size: clamp(1.5rem, 3.3cqi, 2.8rem);
}
.content.kiosk .summary-shell .prayer-panel .event {
  font-size: clamp(1.2rem, 2.6cqi, 2rem);
}
.content.kiosk .summary-shell .prayer-panel .count {
  font-size: clamp(2rem, 5.5cqi, 4.5rem);
}
.content.kiosk .prayer-time .absolute {
  font-size: clamp(1.1rem, 2.3cqi, 1.8rem);
}
.content.kiosk .timetable-shell table {
  font-size: clamp(1rem, 1.9cqi, 1.4rem);
}
.content.kiosk .timetable-shell th,
.content.kiosk .timetable-shell td {
  padding-block: clamp(8px, 1.3cqi, 16px);
}
.kiosk-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}
.kiosk-fullscreen {
  background: var(--secondary-background-color);
  color: var(--primary-text-color);
  font: inherit;
  font-size: .85rem;
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  min-height: 40px;
}
.kiosk-fullscreen:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
@container(max-width:28rem) {
  .content.kiosk { padding: 10px; }
  .content.kiosk .summary-shell .prayer-panel .count {
    font-size: clamp(1.35rem, 5cqi, 2.2rem);
  }
}
@media (prefers-reduced-motion: reduce) {
  .kiosk-fullscreen { transition: none; }
}


.month-toggle,.month-action,.month-nav {
  font: inherit;
  color: var(--primary-text-color);
  background: var(--secondary-background-color);
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  min-height: 40px;
}
/* Monthly actions share the mosque title row. The Gregorian date stays
   directly underneath; compact keeps its accessible More disclosure. */
.summary-shell .header { position: relative; }
/* Only override the original full-width title when an inline toolbar exists.
   Cards with the monthly feature disabled keep their original RTL/date layout. */
.summary-shell .header.has-month-action h2 { min-height: 36px; }
.summary-shell .header:has(.card-action-strip) h2 {
  grid-column: 1;
  grid-row: 1;
}
.card-action-strip {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
  min-width: 0;
  z-index: 3;
}
.card-action-strip .month-toggle,.card-action-strip .month-action {
  display: inline-flex;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 36px;
  min-height: 36px;
  padding: 7px 10px;
  font-size: .95rem;
  line-height: 1.2;
  font-weight: 600;
  white-space: nowrap;
}
.card-action-strip ha-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
  --mdc-icon-size: 1em;
  --ha-icon-size: 1em;
  flex: none;
}
.card-action-strip button span { font-size: inherit; line-height: inherit; }
.compact .header.has-month-action { row-gap: 0; }
.compact .header.has-month-action h2 { padding-inline-end: 86px; }
.card-menu-items button {
  display: flex; align-items: center; gap: 7px; font: inherit;
  min-width: 0; max-width: 100%; overflow-wrap: anywhere; text-align: start;
}
.card-menu-items ha-icon {
  width: 18px; height: 18px; --mdc-icon-size: 18px; --ha-icon-size: 18px;
  flex: none;
}
/* Keep the action alongside the title on small cards: icon-only has an
   accessible label, with the full text returning as soon as it fits. */
@container(max-width:33rem) {
  .card-action-strip button span { display: none; }
  .card-action-strip .month-toggle,.card-action-strip .month-action {
    width: 36px;
    height: 36px;
    padding: 8px;
  }
}
@container(max-width:23rem) {
  /* Keep a two-column title/action row despite the one-column default
     header at mobile widths. Date text then spans the full header width. */
  .header:has(.card-action-strip) {
    grid-template-columns: minmax(0,1fr) max-content;
  }
  .header:has(.card-action-strip) .hijri,
  .header:has(.card-action-strip) .gregorian,
  .header:has(.card-action-strip) .month-description {
    grid-column: 1 / -1;
    grid-row: auto;
  }
  .header:has(.card-action-strip) .gregorian { text-align: end; }
  .header.has-many-month-actions .card-action-strip {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
/* Compact: the More disclosure is a popover anchored to the title row.
   Opening it must not add a grid row or move the countdown panels. */
.card-actions-menu {
  position: absolute;
  inset-block-start: 0;
  inset-inline-end: 0;
  z-index: 6;
  width: max-content;
  max-width: 100%;
}
.card-actions-menu .card-more-toggle {
  display: flex; align-items: center; gap: 3px;
  cursor: pointer; list-style: none;
  border: 1px solid var(--divider-color);
  border-radius: 8px; background: var(--secondary-background-color);
  padding: 7px; min-height: 36px; box-sizing: border-box;
  font-size: .8rem;
}
.card-actions-menu .card-more-toggle::-webkit-details-marker { display: none; }
.card-actions-menu .card-more-toggle ha-icon { width: 18px; height: 18px; --mdc-icon-size: 18px; }
.card-actions-menu .card-more-toggle:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.card-actions-menu .card-menu-items {
  position: absolute;
  inset-block-start: calc(100% + 6px);
  inset-inline-end: 0;
  display: grid; gap: 4px;
  width: min(15rem, calc(100cqi - 4rem));
  box-sizing: border-box;
  padding: 8px; border-radius: 9px;
  border: 1px solid var(--divider-color);
  background: var(--card-background-color);
  box-shadow: 0 8px 24px rgba(0,0,0,.25);
}
.card-actions-menu:not([open]) .card-menu-items { display: none; }
/* Both glass surfaces normally clip their children. Only the expanded menu
   can escape that clip, and it must paint above the timetable and prayer panels. */
.summary-shell:has(.card-actions-menu[open]) {
  overflow: visible;
  z-index: 6;
}
.summary-shell .header:has(.card-actions-menu[open]) { z-index: 7; }
.card-menu-items button { width: 100%; }
.month-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.month-toolbar h3 { font-size: clamp(1rem,2.4cqi,1.5rem); margin: 0; text-align: center; }
.month-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.monthly-shell {
  max-width: 1400px;
  margin: 0 auto;
  padding: clamp(12px,2cqi,22px);
  background: var(--secondary-background-color);
  border-radius: 12px;
}
.monthly-table { font-size: .88rem; }
.monthly-table th,.monthly-table td { white-space: nowrap; padding: 9px 10px; }
.monthly-table .missing-date { opacity: .7; }
.month-toggle:focus-visible,.month-action:focus-visible,.month-nav:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
/* Home Assistant's Panel editor owns the full-height slot and its Edit
   footer. Compacting this custom card cannot reclaim that parent slot,
   and instead creates a tiny card above empty panel space. Preserve the
   normal card proportions during editing; the separate background minimum
   override still prevents the photograph from forcing extra card height. */
.source-summary { border-top: 1px solid var(--divider-color); padding-top: 12px; }
.source-summary p { overflow-wrap: anywhere; font-size: .84rem; }
@container(max-width:28rem) {
  .month-toolbar { flex-wrap: wrap; justify-content: center; }
  .monthly-shell { padding: 8px; }
}


/* The kiosk photo covers the actual canvas, not a cached day-tab frame. */
ha-card.kiosk.has-mosque-background::before,
ha-card.kiosk.has-mosque-background::after {
  inset: 0;
  top: 0;
  left: 0;
  transform: none;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: var(--mosque-background-position, center);
}

/* Kiosk 3.0: three-zone, distance-readable wall display. The source is
   the existing live Home Assistant sensors; no timetable values are inferred. */
.content.kiosk {
  --kiosk-u: clamp(5px, min(.75cqi, 1.15dvh), 12px);
  box-sizing: border-box;
  position: relative;
  width: 100%;
  max-width: none;
  min-height: var(--salah-viewport-card-height, 100dvh);
  margin-inline: auto;
  padding: clamp(12px, 1.7cqi, 28px);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto auto;
  /* Centre the entire prayer display, not the individual panels. If its
     content exceeds the available height, safe alignment starts at the top
     so yesterday/tomorrow, footers and editor controls remain reachable. */
  align-content: safe center;
  justify-items: center;
  gap: clamp(10px, 1.3cqi, 20px);
}
.content.kiosk > .summary-shell,
.content.kiosk > .kiosk-strip,
.content.kiosk > .kiosk-footer,
.content.kiosk > .monthly-shell {
  box-sizing: border-box;
  width: 100%;
  max-width: 1600px;
  margin-inline: auto;
}
/* Entering browser fullscreen changes the viewport origin. Do not reuse the
   previous dashboard's measured available height when centring its contents. */
ha-card.kiosk:fullscreen .content.kiosk {
  min-height: 100dvh;
}
:host([dashboard-editing]) ha-card.kiosk,
:host([dashboard-editing]) .content.kiosk { min-height: 0; }
:host([dashboard-editing]) .content.kiosk {
  grid-template-rows: auto;
  align-content: start;
  justify-items: stretch;
}
.content.kiosk .summary-shell {
  box-sizing: border-box;
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: 100%;
  max-width: 1600px;
  min-width: 0;
  min-height: clamp(270px, 33dvh, 350px);
  margin: 0;
  padding: clamp(18px, 2.2cqi, 34px);
  border-radius: clamp(14px, 1.4cqi, 24px);
}
.content.kiosk .header {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: clamp(10px, 1.6cqi, 28px);
  padding: 0 0 clamp(14px, 1.6cqi, 24px);
  border-bottom: 1px solid var(--divider-color);
  text-align: start;
}
.content.kiosk .header .kiosk-identity {
  min-width: 0;
  text-align: start;
}
.content.kiosk .header h2 {
  grid-column: auto;
  grid-row: auto;
  width: auto;
  min-width: 0;
  margin: 0;
  text-align: start;
  font-size: clamp(1.4rem, 2.65cqi, 3rem);
  font-weight: 750;
  line-height: 1.15;
}
.content.kiosk .kiosk-identity .mosque-select {
  max-width: 100%;
  margin: 0;
  text-align: start;
}
.content.kiosk .kiosk-timezone {
  display: block;
  margin-top: .4em;
  color: var(--secondary-text-color);
  font-size: clamp(.7rem, 1.1cqi, .95rem);
  line-height: 1.4;
}
.content.kiosk .header .kiosk-clock {
  display: grid;
  justify-items: center;
  text-align: center;
  gap: 0;
  min-width: 0;
  white-space: nowrap;
}
.content.kiosk .kiosk-clock-label {
  font-size: clamp(1rem, 1.15cqi, 1.125rem);
  color: var(--secondary-text-color);
  letter-spacing: .04em;
  text-transform: uppercase;
}
.content.kiosk .kiosk-clock-value {
  font-size: clamp(2.25rem, calc(var(--kiosk-u) * 7), 5.3rem);
  font-weight: 750;
  line-height: 1.05;
  letter-spacing: -.025em;
  font-variant-numeric: tabular-nums;
}
.content.kiosk .header .kiosk-dates {
  display: grid;
  /* Leave breathing room beside the overlay icon without changing the
     header grid or moving the rest of the display. */
  padding-inline-end: 18px;
  gap: 3px;
  justify-items: end;
  align-content: center;
  min-width: 0;
  max-width: 100%;
  text-align: end;
}
.content.kiosk .kiosk-dates .date {
  grid-column: auto;
  grid-row: auto;
  min-width: 0;
  font-size: clamp(.92rem, 1.45cqi, 1.25rem);
  line-height: 1.35;
  text-align: end;
  overflow-wrap: anywhere;
}
.content.kiosk .kiosk-dates .hijri { font-weight: 700; }
.content.kiosk .kiosk-dates .gregorian { font-weight: 400; }
.content.kiosk .kiosk-dates .month-description {
  grid-column: auto;
  grid-row: auto;
  max-width: 29rem;
  margin: 3px 0 0;
  font-size: clamp(.8rem, 1.05cqi, 1rem);
  line-height: 1.3;
  text-align: end;
  overflow-wrap: anywhere;
}
.content.kiosk .summary-shell .panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
  gap: 0;
  min-height: 0;
  margin: clamp(14px, 1.6cqi, 26px) 0 0;
  padding: 0;
  border-top: none;
}
.content.kiosk .summary-shell .panel.prayer-panel,
.content.kiosk .summary-shell .panel.prayer-panel[data-panel="salah"] {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: stretch;
  gap: clamp(10px, 1.4cqi, 20px);
  padding: 0 clamp(12px, 2.2cqi, 34px);
  min-width: 0;
  min-height: 0;
}
/* The kiosk's standard flex styling also spaces its two halves vertically.
   Align the shared rows from the top when both countdowns are enabled. */
.content.kiosk .summary-shell .panels:not(.single-panel) > .prayer-panel[data-panel] {
  justify-content: flex-start;
}
.content.kiosk .summary-shell .prayer-panel:first-child { padding-inline-start: 0; }
.content.kiosk .summary-shell .prayer-panel:last-child { padding-inline-end: 0; }
.content.kiosk .summary-shell .prayer-panel + .prayer-panel {
  border-inline-start: 1px solid var(--divider-color);
  padding-inline-start: clamp(18px, 2.2cqi, 34px);
}
.content.kiosk .summary-shell .prayer-panel .label {
  font-size: clamp(.72rem, 1.16cqi, 1rem);
  line-height: 1.3;
}
.content.kiosk .summary-shell .prayer-panel[data-panel="salah"] > .label {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
}
.content.kiosk .kiosk-next-day {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 68%, transparent);
  border-radius: 999px;
  color: var(--primary-text-color);
  background: color-mix(in srgb, var(--primary-color) 18%, transparent);
  font-size: .9em;
  font-weight: 700;
  text-transform: none;
  letter-spacing: normal;
}
.content.kiosk .summary-shell .prayer-panel .event {
  min-height: 0;
  font-size: clamp(1.5rem, calc(var(--kiosk-u) * 4.7), 3.5rem);
  line-height: 1.15;
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .event {
  /* Matching title heights keep both countdown baselines aligned. */
  font-size: clamp(1.5rem, calc(var(--kiosk-u) * 4.7), 3.5rem);
}
.content.kiosk .summary-shell .prayer-panel .count {
  margin: 0;
  font-size: clamp(2rem, min(5.6cqi, 9.2dvh), 6.2rem);
  line-height: 1.05;
  overflow-wrap: normal;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.035em;
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .count {
  /* Same clock size and line-height as Next Salah, different emphasis. */
  font-size: clamp(2rem, min(5.6cqi, 9.2dvh), 6.2rem);
  color: var(--primary-text-color);
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .count span {
  color: inherit;
  font-size: .2em;
  line-height: 1.2;
  letter-spacing: normal;
}
.content.kiosk .summary-shell .prayer-times {
  margin-top: auto;
  padding-top: clamp(12px, 1.3cqi, 20px);
  gap: clamp(12px, 2cqi, 32px);
}
/* Do not bottom-anchor a paired timetable row while the other panel has a
   published sunrise note below it. That note must not offset the clock/time
   baselines of the adjacent panel. */
.content.kiosk .summary-shell .panels:not(.single-panel) > .prayer-panel .prayer-times {
  margin-top: 0;
}
.content.kiosk .summary-shell .prayer-time .absolute {
  font-size: clamp(1.15rem, 2.1cqi, 1.85rem);
}
.content.kiosk .summary-shell .prayer-time .label {
  font-size: clamp(1rem, 1.13cqi, 1.125rem);
}
.content.kiosk .summary-shell .panel-silhouette { opacity: .07; }

/* Five daily tiles replace the scrolling timetable only in kiosk mode. */
.content.kiosk .kiosk-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: clamp(6px, .75cqi, 14px);
  width: 100%;
  min-width: 0;
}
.content.kiosk .kiosk-tile {
  box-sizing: border-box;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: clamp(8px, 1.1cqi, 14px);
  padding: clamp(12px, 1.2cqi, 20px);
  color: var(--primary-text-color);
  border: 1px solid var(--divider-color);
  border-radius: clamp(12px, 1.1cqi, 18px);
  background: color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) 97%, transparent);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}
.content.kiosk .kiosk-tile.is-past { opacity: .88; }
.content.kiosk .kiosk-tile.is-current {
  border-color: color-mix(in srgb, var(--primary-text-color) 55%, transparent);
  background: color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) 96%, transparent);
}
.content.kiosk .kiosk-tile.is-next {
  color: #fff;
  background: color-mix(in srgb, var(--primary-color) 74%, #10202b);
  border-color: color-mix(in srgb, var(--primary-color) 55%, #fff);
}
/* A second, quieter indication for the next published Jamaat in today's strip. */
.content.kiosk .kiosk-tile.is-next-jamaat {
  border-color: color-mix(in srgb, var(--primary-text-color) 66%, var(--primary-color));
  box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--primary-text-color) 44%, transparent);
}
.content.kiosk .kiosk-tile-name {
  margin: 0;
  font-size: clamp(.95rem, 1.6cqi, 1.45rem);
  font-weight: 700;
  line-height: 1.25;
}
.content.kiosk .kiosk-tile-name .prayer-labels {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px;
}
.content.kiosk .kiosk-tile-name .label-separator { display: none; }
.content.kiosk .kiosk-tile-times {
  display: flex;
  justify-content: space-between;
  gap: clamp(8px, 1.5cqi, 22px);
}
.content.kiosk .kiosk-tile-time { min-width: 0; }
.content.kiosk .kiosk-tile-label {
  display: block;
  margin-bottom: .4em;
  color: inherit;
  opacity: .96;
  font-size: clamp(1rem, 1.13cqi, 1.125rem);
}
.content.kiosk .kiosk-tile-time strong {
  font-size: clamp(1.1rem, 1.7cqi, 1.65rem);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.content.kiosk .kiosk-tile-jamaat-values {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  align-items: baseline;
}
.content.kiosk .kiosk-tile-jumuah { font-size: .75rem; }
.content.kiosk .kiosk-tile-empty,
.content.kiosk .kiosk-strip-empty { padding: 14px; }

/* Same footer alignment as the provided mockup; controls stay reachable. */
.content.kiosk .kiosk-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: clamp(10px, 1cqi, 18px);
  width: 100%;
  min-width: 0;
}
.content.kiosk .kiosk-footer-info {
  grid-column: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  gap: 5px;
}
.content.kiosk .kiosk-footer-note {
  color: var(--primary-text-color);
  opacity: .9;
  margin: 0;
  font-size: clamp(.7rem, .9cqi, .9rem);
}
.content.kiosk .kiosk-day-tabs {
  grid-column: 2;
  justify-self: center;
  display: flex;
  width: max-content;
  max-width: 100%;
  gap: 4px;
  padding: 4px;
  margin: 0;
  border: 1px solid var(--divider-color);
  border-radius: 14px;
  background: color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) 85%, transparent);
}
.content.kiosk .kiosk-day-tabs .date-tab:not([aria-pressed="true"]) {
  color: var(--primary-text-color);
  opacity: .95;
}
.content.kiosk .kiosk-day-tabs .date-tab {
  min-height: clamp(40px, 6dvh, 62px);
  min-width: clamp(76px, 7cqi, 115px);
  padding: 8px clamp(10px, 1cqi, 18px);
  font-size: clamp(.8rem, 1.1cqi, 1rem);
  border-radius: 10px;
}
.content.kiosk .kiosk-footer .kiosk-toolbar {
  grid-column: 3;
  justify-self: end;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  margin: 0;
  position: static;
  inset: auto;
}
/* One icon in the glass itself, outside header/grid flow. */
.content.kiosk .summary-shell > .kiosk-fullscreen {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 5;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  min-height: 30px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, .16);
  border-radius: 50%;
  color: #fff;
  background: rgba(0, 0, 0, .28);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  cursor: pointer;
  line-height: 1;
}
.content.kiosk .summary-shell > .kiosk-fullscreen ha-icon {
  width: 17px;
  height: 17px;
  --mdc-icon-size: 17px;
}
.content.kiosk .summary-shell > .kiosk-fullscreen:hover {
  background: rgba(0, 0, 0, .42);
}
.content.kiosk .summary-shell > .kiosk-fullscreen:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.content.kiosk .kiosk-toolbar .card-action-strip {
  grid-column: auto;
  grid-row: auto;
}
.content.kiosk .kiosk-toolbar .card-actions-menu { position: relative; inset: auto; }
.content.kiosk .kiosk-footer-info .background-credit {
  display: block;
  max-width: 100%;
  margin: 0;
  font-size: clamp(.73rem, .9cqi, .87rem);
  line-height: 1.3;
  opacity: .84;
  text-align: start;
  overflow-wrap: anywhere;
}
.content.kiosk .kiosk-footer-info .background-credit a {
  overflow-wrap: anywhere;
}

/* Portrait, tablet and narrow Cast views must scroll rather than clip. */
@container(max-width:60rem) {
  .content.kiosk .header { grid-template-columns: minmax(0, 1fr) auto; }
  .content.kiosk .header .kiosk-dates {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-items: center;
    text-align: center;
  }
  .content.kiosk .kiosk-dates .date,
  .content.kiosk .kiosk-dates .month-description { text-align: center; }
  .content.kiosk .kiosk-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .content.kiosk .kiosk-footer { grid-template-columns: 1fr auto; }
  .content.kiosk .kiosk-footer-info { grid-column: 1 / -1; }
  .content.kiosk .kiosk-day-tabs { grid-column: 1; }
  .content.kiosk .kiosk-footer .kiosk-toolbar { grid-column: 2; }
}
@container(max-width:40rem) {
  .content.kiosk .header { grid-template-columns: 1fr; text-align: center; }
  .content.kiosk .header .kiosk-identity {
    text-align: center;
    max-width: calc(100% - 40px);
    margin-inline: auto;
  }
  .content.kiosk .header h2 { text-align: center; }
  .content.kiosk .header .kiosk-clock { grid-column: 1; }
  .content.kiosk .header .kiosk-dates { grid-column: 1; grid-row: auto; }
  .content.kiosk .summary-shell .panels { grid-template-columns: 1fr; }
  .content.kiosk .summary-shell .prayer-panel + .prayer-panel {
    border-inline-start: 0;
    border-block-start: 1px solid var(--divider-color);
    padding: clamp(14px, 2cqi, 20px) 0 0;
  }
  .content.kiosk .summary-shell .panel.prayer-panel { padding-inline: 0; }
  .content.kiosk .summary-shell .prayer-panel .count,
  .content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .count {
    font-size: clamp(2.2rem, 9cqi, 4.5rem);
  }
  .content.kiosk .kiosk-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .content.kiosk .kiosk-footer { grid-template-columns: 1fr; }
  .content.kiosk .kiosk-footer-info { grid-column: 1; align-items: center; text-align: center; }
  .content.kiosk .kiosk-day-tabs { grid-column: 1; justify-self: center; }
  .content.kiosk .kiosk-footer .kiosk-toolbar {
    grid-column: 1; justify-self: center; justify-content: center;
  }
}
@container(max-width:24rem) {
  .content.kiosk { padding: 10px; }
  .content.kiosk .summary-shell { padding: 14px; min-height: 0; }
  .content.kiosk .kiosk-tile-times { flex-wrap: wrap; }
  .content.kiosk .kiosk-tile-name { font-size: .95rem; }
  .content.kiosk .kiosk-day-tabs .date-tab { min-width: 0; }
}
@media (prefers-reduced-transparency: reduce), (prefers-contrast: more) {
  .content.kiosk .kiosk-tile,
  .content.kiosk .kiosk-day-tabs {
    background: var(--secondary-background-color);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}

`;
