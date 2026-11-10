/** Ordered Salah Timetable styles: foundation section. */
export const FOUNDATION_CSS = `
.background-credit { display: block; text-align: end; margin-top: 10px; font-size: .7rem; opacity: .75; }
.background-credit a { color: var(--secondary-text-color); text-decoration: underline; text-underline-offset: 2px; }
.background-credit a:focus-visible { outline: 2px solid var(--primary-color); }

/* Fill the visible dashboard space from the card's real top edge, not
   a whole viewport minus a guessed HA header height. JavaScript measures
   --salah-viewport-card-height after layout and on viewport changes.
   Content taller than the screen is never constrained or clipped. */
ha-card.has-mosque-background {
  background: var(--ha-card-background,var(--card-background-color));
  min-height: var(--salah-viewport-card-height, calc(100dvh - var(--header-height, 0px)));
}
/* Keep the full photograph on the dashboard, but let Home Assistant's
   edit-card controls remain near the content while editing or previewing. */
:host([dashboard-editing]) ha-card.has-mosque-background {
  min-height: 0;
}
ha-card.has-mosque-background::before {
  content: "";
  position: absolute;
  top: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: var(--mosque-photo-frame-width,calc(100% - 2px));
  height: max(calc(100% - 2px),var(--mosque-photo-frame-height,100%));
  z-index: 0;
  pointer-events: none;
  background-image: var(--mosque-background-image);
  background-origin: padding-box;
  background-clip: padding-box;
  background-position: var(--mosque-background-position,center);
  background-size: cover;
  background-repeat: no-repeat;
}
ha-card.has-mosque-background .content { position: relative; z-index: 1; }
@media (prefers-contrast: more), (prefers-reduced-transparency: reduce) {
  ha-card.has-mosque-background::before { display: none; }
}

.date-tabs {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 6px;
  padding: 4px;
  background: var(--secondary-background-color);
  border-radius: 12px;
  margin: 0 0 16px;
}
.date-tab {
  border: 0;
  border-radius: 9px;
  font: inherit;
  font-weight: 600;
  background: transparent;
  color: var(--secondary-text-color);
  cursor: pointer;
}
.date-tab {
  padding: 10px 5px;
}
.date-tab[aria-pressed="true"] {
  background: var(--primary-color);
  color: var(--text-primary-color,#fff);
}
.date-tab:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.selected-date {
  font-size: .9rem;
  font-weight: 600;
  color: var(--secondary-text-color);
  margin-bottom: 12px;
}
.prayer-panel {
  gap: 8px;
}
.prayer-panel .event {
  min-height: 1.7em;
}
.prayer-panel .count {
  margin: 4px 0 8px;
}
.prayer-times {
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 10px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--divider-color);
}
.prayer-time {
  min-width: 0;
}
.prayer-time .label {
  margin: 0 0 5px;
}
.prayer-time .absolute {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--primary-text-color);
  margin: 0;
}
.prayer-panel[data-panel="jamaat"] {
  justify-content: space-between;
}
.fajr-sunrise {
  margin-top: 5px;
}
:host {
  display: block;
  container-type: inline-size;
  color: var(--primary-text-color);
  font-family: var(--paper-font-body1_-_font-family,inherit);
}
ha-card {
  display: block;
  overflow: hidden;
  background: var(--ha-card-background,var(--card-background-color));
  border-radius: var(--ha-card-border-radius,12px);
}
.content {
  padding: 20px;
}
.header {
  display: flex;
  gap: 12px;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
}
h2 {
  font-size: 1.35rem;
  margin: 0;
  overflow-wrap: anywhere;
}
.date {
  color: var(--secondary-text-color);
  font-size: .9rem;
}
.panels {
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 12px;
  margin: 18px 0;
}
.panel {
  border-radius: 10px;
  padding: 14px;
  background: var(--secondary-background-color);
  min-width: 0;
}
.label {
  color: var(--secondary-text-color);
  font-size: .83rem;
  margin-bottom: 5px;
}
.event {
  font-weight: 600;
  font-size: 1.05rem;
}
.count {
  font-variant-numeric: tabular-nums;
  font-size: clamp(1.6rem,6cqi,2.2rem);
  color: var(--primary-color);
  margin-top: 7px;
  overflow-wrap: anywhere;
}
.absolute {
  color: var(--secondary-text-color);
  font-size: .85rem;
  margin-top: 5px;
}
.table-scroll {
  max-width: 100%;
  overflow-x: auto;
}
thead th {
  overflow-wrap: anywhere;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: .97rem;
}
th,td {
  padding: 10px 6px;
  border-bottom: 1px solid var(--divider-color);
  text-align: end;
  font-variant-numeric: tabular-nums;
}
th:first-child,td:first-child {
  text-align: start;
}
th {
  color: var(--secondary-text-color);
  font-size: .83rem;
  font-weight: 500;
}
tr:last-child td,tr:last-child th {
  border-bottom: 0;
}
.ramadan {
  border-top: 1px solid var(--divider-color);
  margin-top: 14px;
  padding-top: 14px;
}
.ramadan h3 {
  font-size: 1rem;
  margin: 0 0 12px;
}
.ramadan-grid {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 12px;
}
.ramadan .count {
  font-size: 1.1rem;
}
.note {
  color: var(--secondary-text-color);
  font-size: .83rem;
  margin: 12px 0 0;
}
.empty {
  padding: 22px;
  color: var(--secondary-text-color);
  line-height: 1.5;
}
.disconnected {
  color: var(--error-color);
  font-size: .85rem;
  margin: 8px 0;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
@media(max-width:420px) {
  .content {
    padding: 14px;
  }
  .panels {
    gap: 8px;
  }
  .panel {
    padding: 10px;
  }
  .count {
    font-size: 1.6rem;
  }
  .ramadan-grid {
    grid-template-columns: 1fr 1fr;
  }
  .ramadan-grid>:last-child {
    grid-column: 1/-1;
  }
  th,td {
    padding: 9px 3px;
    font-size: .9rem;
  }
}
.progress-help {
  font-size: .72rem;
  color: var(--secondary-text-color);
  margin-top: 5px;
}
.scroll-help {
  display: none;
  font-size: .75rem;
}
.event,.absolute,.date,.label {
  overflow-wrap: anywhere;
}
bdi {
  unicode-bidi: isolate;
}
.prayer-labels {
  display: inline-flex;
  flex-wrap: wrap;
  gap: .3em;
  align-items: baseline;
}
.prayer-labels bdi {
  overflow-wrap: anywhere;
}
.label-separator {
  font-weight: 400;
  color: var(--secondary-text-color);
}
progress::-webkit-progress-bar {
  background: var(--divider-color);
}
progress::-webkit-progress-value {
  background: var(--primary-color);
}
progress::-moz-progress-bar {
  background: var(--primary-color);
}
progress {
  display: block;
  width: 100%;
  height: 4px;
  margin-top: 12px;
  border: 0;
  accent-color: var(--primary-color);
}
.next-prayer {
  background: color-mix(in srgb,var(--primary-color) 12%,transparent);
}
.next-prayer th,.next-prayer td {
  font-weight: 700;
  font-size: 1.05em;
}
.past-prayer {
  color: var(--secondary-text-color);
}
.congregation-time {
  white-space: nowrap;
}
.hijri {
  flex-basis: 100%;
}
.compact th,.compact td {
  padding-top: 6px;
  padding-bottom: 6px;
}
.compact .panel {
  padding: 10px;
}
.compact .count {
  font-size: 1.6rem;
}
table {
  table-layout: fixed;
  min-width: 22rem;
}
th:first-child {
  width: 30%;
}
.panels:has(>:only-child) {
  grid-template-columns: 1fr;
}
@container(max-width:26rem) {
  .scroll-help {
    display: block;
  }
  .panels {
    grid-template-columns: 1fr;
  }
  .count {
    font-size: 1.7rem;
  }
  .ramadan-grid {
    grid-template-columns: 1fr 1fr;
  }
  .ramadan-grid>:last-child {
    grid-column: 1/-1;
  }
}
`;
