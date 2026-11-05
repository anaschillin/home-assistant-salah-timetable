/** Theme-aware card styles. Keep responsive and preference overrides in cascade order. */
export const CARD_CSS = `
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
/* HaCasa-inspired translucent surfaces, without external assets or dependencies. */
ha-card {
  position: relative;
  isolation: isolate;
}
ha-card::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: radial-gradient(ellipse at 95% 0%,color-mix(in srgb,var(--primary-color) 12%,transparent),transparent 55%);
}
.panel {
  background: color-mix(in srgb,var(--secondary-background-color) 82%,transparent);
  box-shadow: 0 5px 18px rgba(0,0,0,.055);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter:blur(12px)
}
.panel[data-panel="salah"] {
  background: color-mix(in srgb,var(--primary-color) 13%,var(--ha-card-background,var(--card-background-color)));
}
.table-scroll {
  background: color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 92%,transparent);
}
@media(prefers-contrast:more) {
  .panel,.panel[data-panel="salah"],.table-scroll {
    background: var(--card-background-color);
    border: 2px solid var(--primary-text-color);
    box-shadow: none;
  }
}
@media(prefers-reduced-transparency:reduce) {
  .panel,.table-scroll {
    backdrop-filter: none;
    -webkit-backdrop-filter:none;
    background: var(--secondary-background-color);
  }
}
/* Theme-aware card edges without a surrounding drop-shadow. */
ha-card {
  border: 1px solid var(--divider-color);
  box-shadow: none;
}
.content {
  padding: clamp(14px,3cqi,24px);
}
.header {
  align-items: flex-start;
  gap: 6px 16px;
  margin-bottom: 18px;
}
.header h2 {
  font-size: clamp(1.25rem,3cqi,1.65rem);
  font-weight: 700;
  letter-spacing: -.025em;
  flex-basis: 100%;
}
.date {
  font-size: .82rem;
}
.hijri {
  flex-basis: auto;
  font-weight: 600;
  color: var(--primary-text-color);
}
.panels {
  gap: 12px;
  margin: 0 0 22px;
}
.panel {
  padding: clamp(14px,2.6cqi,20px);
  border: 1px solid var(--divider-color);
  border-radius: 16px;
  background: var(--secondary-background-color);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.panel[data-panel="salah"] {
  background: color-mix(in srgb,var(--primary-color) 9%,var(--ha-card-background,var(--card-background-color)));
  border-color: color-mix(in srgb,var(--primary-color) 22%,var(--divider-color));
}
.panel .label {
  font-size: .73rem;
  letter-spacing: .075em;
  text-transform: uppercase;
  font-weight: 700;
}
.panel .event {
  font-size: 1.2rem;
}
.panel .count {
  font-size: clamp(1.65rem,5.5cqi,2.65rem);
  font-weight: 750;
  letter-spacing: -.045em;
  margin: 4px 0;
}
.panel .absolute {
  font-size: .88rem;
}
.panel progress {
  height: 6px;
  border-radius: 99px;
  overflow: hidden;
  margin-top: 10px;
}
.table-scroll {
  border: 1px solid var(--divider-color);
  border-radius: 14px;
}
table {
  min-width: 0;
  table-layout: auto;
}
thead {
  background: var(--secondary-background-color);
}
th,td {
  padding: 12px 10px;
}
thead th {
  font-size: .73rem;
  letter-spacing: .04em;
  text-transform: uppercase;
}
tbody tr:not(:last-child) {
  border-bottom: 1px solid var(--divider-color);
}
tbody tr th,tbody tr td {
  border-bottom: 0;
}
.next-prayer {
  background: color-mix(in srgb,var(--primary-color) 13%,transparent);
  box-shadow: inset 3px 0 var(--primary-color);
}
.past-prayer {
  opacity: 1;
}
.past-prayer th,.past-prayer td {
  color: inherit;
}
.ramadan {
  margin-top: 20px;
}
.ramadan-grid>div {
  background: var(--secondary-background-color);
  border: 1px solid var(--divider-color);
  padding: 14px;
  border-radius: 12px;
}
.compact {
  padding: 12px;
}
.compact .panel {
  padding: 12px;
}
.compact .panel .count {
  font-size: 1.65rem;
}
@container(max-width:28rem) {
  .panels {
    grid-template-columns: 1fr;
  }
  .table-scroll {
    border: 0;
    border-radius: 0;
  }
  table {
    width: 100%;
    min-width: 0;
    font-size: .86rem;
  }
  th,td {
    padding: 9px 4px;
  }
  th:first-child {
    width: auto;
  }
  .panel .count {
    font-size: 2rem;
  }
  .ramadan-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media(prefers-reduced-motion:no-preference) {
  .panel,.next-prayer {
    transition: background-color .2s ease,border-color .2s ease;
  }
}

/* Compact, timetable-first dashboard: keep summaries informative without
   making the primary published timetable require excessive scrolling. */
.header {
  margin-bottom: 12px;
  gap: 3px 12px;
}
.header h2 {
  line-height: 1.25;
  font-size: clamp(1.15rem, 3cqi, 1.45rem);
}
.mosque-select {
  box-sizing: border-box;
  display: block;
  max-width: 100%;
  width: fit-content;
  font: inherit;
  font-weight: inherit;
  line-height: 1.25;
  padding: 2px 26px 2px 0;
  color: var(--primary-text-color);
  background: transparent;
  border: 0;
  cursor: pointer;
  text-overflow: ellipsis;
}
.mosque-select option {
  background: var(--ha-card-background,var(--card-background-color));
  color: var(--primary-text-color);
}
.mosque-select:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.panels {
  gap: 10px;
  margin: 0 0 12px;
}
.panel.prayer-panel {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: 12px 14px;
  gap: 3px;
}
.prayer-panel .event {
  font-size: 1rem;
  min-height: 0;
  line-height: 1.3;
}
.prayer-panel .label {
  margin: 0;
  font-size: .65rem;
  letter-spacing: .055em;
}
.panel.prayer-panel .count {
  font-size: clamp(1.15rem, 3.8cqi, 1.85rem);
  line-height: 1.18;
  margin: 2px 0 4px;
}
.prayer-panel .count span {
  font-size: .75em;
  letter-spacing: normal;
}
.prayer-panel .prayer-times {
  margin-top: 4px;
  padding-top: 8px;
  gap: 5px;
}
.prayer-panel .prayer-time .label {
  margin-bottom: 2px;
  font-size: .6rem;
}
.prayer-panel .prayer-time .absolute {
  margin: 0;
  font-size: .82rem;
}
.prayer-panel .panel-silhouette {
  position: absolute;
  inset-block-start: 25px;
  inset-inline-end: 8px;
  width: min(30%, 80px);
  color: var(--primary-color);
  opacity: .13;
  z-index: 0;
  pointer-events: none;
}
.panel-silhouette svg {
  display: block;
  width: 100%;
  height: auto;
  fill: currentColor;
}
.prayer-panel > :not(.panel-silhouette) {
  position: relative;
  z-index: 1;
}
.timetable-shell {
  min-width: 0;
  border: 1px solid var(--divider-color);
  border-radius: 14px;
  overflow: hidden;
  background: transparent;
}
.timetable-shell .table-scroll {
  border: 0;
  border-radius: 0;
  background: transparent;
}
.timetable-shell .selected-date {
  padding: 9px 12px 0;
  margin-bottom: 6px;
}
.timetable-shell .empty {
  padding: 14px;
}
.timetable-shell .scroll-help {
  margin: 0;
  padding: 6px 10px;
}
.date-tabs {
  margin: 0;
  padding: 4px;
  border-radius: 0;
  border-top: 1px solid var(--divider-color);
  background: var(--secondary-background-color);
}
.date-tab {
  min-width: 0;
  min-height: 34px;
  padding: 7px 4px;
  font-size: .79rem;
}
/* A real grid reserves a full row for the month description. The previous
   flex-basis:100% + max-width combination let the description share a line
   with the dates on tablet and desktop. */
.header {
  display: grid;
  grid-template-columns: minmax(0,1fr) max-content;
  align-items: start;
  justify-content: stretch;
  column-gap: 16px;
  row-gap: 5px;
}
.header h2 {
  grid-column: 1 / -1;
  min-width: 0;
}
.header .hijri {
  grid-column: 1;
  grid-row: 2;
  min-width: 0;
  overflow-wrap: anywhere;
}
.header .gregorian {
  grid-column: 2;
  grid-row: 2;
  text-align: end;
  white-space: normal;
}
.header .month-description {
  grid-column: 1 / -1;
  grid-row: 3;
  width: 100%;
  max-width: none;
  min-width: 0;
  margin: 2px 0 0;
  font-size: .82rem;
  line-height: 1.45;
  font-weight: 400;
  color: var(--secondary-text-color);
  overflow-wrap: anywhere;
}
/* When card space is truly narrow, dates stack instead of competing for
   horizontal space. Use container width, not overall device viewport. */
@container(max-width:23rem) {
  .header { grid-template-columns: minmax(0,1fr); }
  .header .hijri,.header .gregorian,.header .month-description {
    grid-column: 1;
    grid-row: auto;
  }
  .header .gregorian { text-align: start; }
}
/* Full-bleed mosque photograph across the entire canvas allocated by
   Home Assistant. Limit only the inner content width, never the background.
   The dashboard layout still determines the available canvas width. */
ha-card {
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  margin-inline: 0;
  /* Keep all depth within the translucent summary; an outer shadow creates
     a dark halo across the full-width photograph and dashboard edges. */
  box-shadow: none;
  border-color: color-mix(in srgb,var(--primary-color) 17%,var(--divider-color));
}
.content {
  box-sizing: border-box;
  width: 100%;
  max-width: 1160px;
  margin-inline: auto;
}
/* Photograph stays un-tinted outside the two glass panels; only their
   own surfaces refract/soften the scene underneath. */
ha-card.has-mosque-background .content {
  z-index: 1;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
/* Blur only the photograph at the rim, never the timetable or lettering. */
ha-card.has-mosque-background::after {
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
  background-size: cover;
  background-position: var(--mosque-background-position,center);
  filter: blur(14px);
  opacity: .14;
  -webkit-mask-image: radial-gradient(ellipse at center, transparent 55%, #000 100%);
  mask-image: radial-gradient(ellipse at center, transparent 55%, #000 100%);
}
@media (prefers-contrast: more), (prefers-reduced-transparency: reduce) {
  ha-card.has-mosque-background::after { display: none; }
  ha-card.has-mosque-background .content {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    background: transparent;
  }
}
/* Legible CSS-first liquid glass: both panels use the same high-contrast
   glass substrate. The full-canvas photograph remains entirely untinted.
   Text stays DOM based; no shader, network request or animation required. */
.summary-shell,
.timetable-shell {
  position: relative;
  isolation: isolate;
  min-width: 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb,var(--primary-text-color) 20%,transparent);
  border-radius: 18px;
  /* Balanced 84%-88% photo-through glass: more of the mosque is visible
     than the previous 92%-95% charcoal surface, while still materially
     stronger than the washed-out 59%-72% version. Both cards share it. */
  background: linear-gradient(135deg,
    color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 84%,transparent),
    color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 88%,transparent) 50%,
    color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 84%,transparent));
  color: var(--primary-text-color);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.13),
    inset 0 -1px 0 rgba(255,255,255,.05),
    0 6px 18px rgba(0,0,0,.10);
  backdrop-filter: blur(20px) saturate(115%);
  -webkit-backdrop-filter: blur(20px) saturate(115%);
}
/* Edge lighting and a delicate curved highlight simulate the thickness of
   refractive glass; keep highlight behind text, table and interactive tabs. */
.summary-shell::before,
.timetable-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  border-radius: inherit;
  pointer-events: none;
  background:
    linear-gradient(118deg,rgba(255,255,255,.055),transparent 22%,transparent 78%,rgba(255,255,255,.025)),
    radial-gradient(ellipse at 8% 0%,rgba(255,255,255,.045),transparent 40%);
}
.summary-shell > *,
.timetable-shell > * {
  position: relative;
  z-index: 1;
}
.summary-shell {
  margin-bottom: 16px;
  padding: clamp(14px,2.4cqi,22px);
}
.summary-shell .header { margin: 0; }
.summary-shell .panels {
  grid-template-columns: repeat(2,minmax(0,1fr));
  align-items: stretch;
  margin: 14px 0 0;
  padding-top: 14px;
  gap: 0;
  border-top: 1px solid color-mix(in srgb,var(--primary-text-color) 14%,transparent);
}
/* Both countdown halves get exactly the same transparent glass formatting. */
.summary-shell .panel.prayer-panel,
.summary-shell .panel.prayer-panel[data-panel="salah"] {
  min-width: 0;
  padding: 8px 14px 10px;
  gap: 4px;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
.summary-shell .prayer-panel + .prayer-panel {
  border-inline-start: 1px solid color-mix(in srgb,var(--primary-text-color) 14%,transparent);
}
.summary-shell .prayer-panel .prayer-times {
  border-top-color: color-mix(in srgb,var(--primary-text-color) 14%,transparent);
}
.summary-shell .prayer-panel .panel-silhouette { opacity: .08; }
/* Do not add an extra translucent layer on top of the timetable glass:
   its header, rows and footer all see the same substrate as the summary. */
.timetable-shell thead,
.timetable-shell .date-tabs,
.timetable-shell .table-scroll {
  background: transparent;
}
.timetable-shell .date-tabs {
  border-top-color: color-mix(in srgb,var(--primary-text-color) 18%,transparent);
}
.summary-shell .date,
.summary-shell .month-description,
.summary-shell .label,
.timetable-shell thead th,
.timetable-shell tbody th,
.timetable-shell .fajr-end,
.timetable-shell .date-tab:not([aria-pressed="true"]) {
  color: color-mix(in srgb,var(--primary-text-color) 85%,var(--ha-card-background,var(--card-background-color)));
}
.summary-shell .prayer-time .label,
.timetable-shell .selected-date {
  color: color-mix(in srgb,var(--primary-text-color) 85%,var(--ha-card-background,var(--card-background-color)));
}
@container(max-width:21rem) {
  .summary-shell .panels { grid-template-columns: 1fr; }
  .summary-shell .prayer-panel + .prayer-panel {
    border-inline-start: 0;
    border-block-start: 1px solid color-mix(in srgb,var(--primary-text-color) 14%,transparent);
  }
}
/* Do not rely on backdrop-filter support or transparency for legibility. */
@supports not (backdrop-filter: blur(1px)) {
  .summary-shell,.timetable-shell {
    background: var(--secondary-background-color);
    -webkit-backdrop-filter: none;
  }
}
@media (prefers-contrast: more), (prefers-reduced-transparency: reduce) {
  .summary-shell,.timetable-shell {
    background: var(--secondary-background-color);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    box-shadow: none;
  }
  .summary-shell::before,.timetable-shell::before { display: none; }
  .timetable-shell thead,.timetable-shell .date-tabs {
    background: var(--secondary-background-color);
  }
}
@media (prefers-contrast: more) {
  .summary-shell,.timetable-shell { border: 2px solid var(--primary-text-color); }
  .summary-shell .panels,
  .summary-shell .prayer-panel + .prayer-panel,
  .summary-shell .prayer-panel .prayer-times,
  .timetable-shell .date-tabs { border-color: var(--primary-text-color); }
}
@container(max-width:28rem) {
  .panels {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }
  .panel.prayer-panel {
    padding: 10px;
  }
  .panel.prayer-panel .count {
    font-size: clamp(1.1rem, 3.7cqi, 1.65rem);
  }
  .prayer-panel .panel-silhouette {
    width: min(28%, 56px);
  }
}
@container(max-width:21rem) {
  .panels {
    grid-template-columns: 1fr;
  }
}


/* Calculated auxiliaries never blend into the published daily prayer table. */
.night-calculations {
  border-top: 1px solid var(--divider-color);
  margin: 14px auto 0;
  padding: 14px clamp(10px,2cqi,20px);
  max-width: 1400px;
  border-radius: 10px;
  background: var(--secondary-background-color);
}
.night-calculations h3 {
  font-size: 1rem;
  margin: 0 0 12px;
}
.night-grid {
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 12px;
}
.night-cell { min-width: 0; }
.night-calculations .note { line-height: 1.45; }
@container(max-width:21rem) {
  .night-grid { grid-template-columns: 1fr; }
}

/* Kiosk is strictly opt-in. Responsive sizing avoids clipping in phone WebViews. */
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
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
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
.content.kiosk .summary-shell .prayer-panel .event {
  min-height: 0;
  font-size: clamp(1.5rem, calc(var(--kiosk-u) * 4.7), 3.5rem);
  line-height: 1.15;
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .event {
  font-size: clamp(1.3rem, calc(var(--kiosk-u) * 3.7), 2.85rem);
}
.content.kiosk .summary-shell .prayer-panel .count {
  margin: 0;
  font-size: clamp(3rem, calc(var(--kiosk-u) * 13.5), 9.25rem);
  line-height: 1.05;
  overflow-wrap: normal;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.035em;
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .count {
  font-size: clamp(2.1rem, calc(var(--kiosk-u) * 7), 5.4rem);
  color: var(--primary-text-color);
}
.content.kiosk .summary-shell .prayer-panel[data-panel="jamaat"] .count span {
  color: inherit;
}
.content.kiosk .summary-shell .prayer-times {
  margin-top: auto;
  padding-top: clamp(12px, 1.3cqi, 20px);
  gap: clamp(12px, 2cqi, 32px);
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
  background: color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) 94%, transparent);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
.content.kiosk .kiosk-tile.is-past { opacity: .72; }
.content.kiosk .kiosk-tile.is-current {
  border-color: color-mix(in srgb, var(--primary-text-color) 55%, transparent);
  background: color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) 96%, transparent);
}
.content.kiosk .kiosk-tile.is-next {
  color: #fff;
  background: color-mix(in srgb, var(--primary-color) 74%, #10202b);
  border-color: color-mix(in srgb, var(--primary-color) 55%, #fff);
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
  opacity: .82;
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
.content.kiosk .kiosk-fullscreen {
  min-height: clamp(42px, 6dvh, 62px);
  padding: 8px clamp(12px, 1.2cqi, 22px);
  white-space: nowrap;
  font-size: clamp(.75rem, 1cqi, .95rem);
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
  .content.kiosk .header .kiosk-identity { text-align: center; }
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
  .content.kiosk .summary-shell .prayer-panel .count { font-size: clamp(2.2rem, 9cqi, 4.5rem); }
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

/** Card configuration editor styles, scoped to its separate shadow root. */
export const EDITOR_CSS = `
.reminder-setup { font: inherit; color: var(--primary-text-color); background: var(--secondary-background-color); border: 1px solid var(--divider-color); border-radius: 8px; padding: 8px 12px; min-height: 44px; cursor: pointer; justify-self: start; }
.reminder-setup[hidden] { display: none; }
.reminder-setup:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

:host { display: block; container-type: inline-size; }
.form { display: grid; gap: 14px; padding: 12px 0; color: var(--primary-text-color); }
.help { color: var(--secondary-text-color); font-size: .85rem; line-height: 1.45; }
.error { color: var(--error-color); }
.setting select:focus-visible,
.editor-section-toggle:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.mosque-options { display: grid; gap: 7px; }
.mosque-options[hidden] { display: none; }
.mosque-options-heading { font-weight: 600; }
.mosque-options-hint { font-size: .8rem; line-height: 1.35; color: var(--secondary-text-color); }
.mosque-options-list { display: grid; }
.mosque-choice { display: grid; grid-template-columns: 32px minmax(0,1fr) 34px 34px; gap: 6px; align-items: center; min-width: 0; padding: 8px 0; border-top: 1px solid var(--divider-color); }
.mosque-choice[data-selected="false"] { opacity: .75; }
.mosque-choice-label { display: flex; align-items: center; gap: 8px; min-width: 0; overflow-wrap: anywhere; font-size: .88rem; }
.mosque-choice input { flex-shrink: 0; accent-color: var(--primary-color); }
.mosque-first { font-size: .7rem; color: var(--primary-color); }
.mosque-grip { width: 32px; height: 34px; padding: 4px; border: 0; background: transparent; border-radius: 7px; color: var(--secondary-text-color); cursor: grab; touch-action: none; user-select: none; }
.mosque-grip:active:not(:disabled) { cursor: grabbing; }
.mosque-grip:disabled { opacity: .3; cursor: default; }
.mosque-grip ha-icon { width: 20px; height: 20px; --mdc-icon-size: 20px; }
.mosque-grip:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 1px; }
.mosque-choice button { width: 34px; height: 34px; padding: 3px; border: 0; background: transparent; border-radius: 7px; color: var(--primary-text-color); display: grid; place-items: center; cursor: pointer; }
.mosque-choice button:disabled { opacity: .3; cursor: default; }
.mosque-choice button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 1px; }
.mosque-choice button ha-icon { width: 18px; height: 18px; --mdc-icon-size: 18px; }
@container(max-width: 22rem) { .mosque-choice { grid-template-columns: 30px minmax(0,1fr) 32px 32px; } }
.setting {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.setting-copy { display: grid; gap: 5px; min-width: 0; overflow-wrap: anywhere; }
.setting-label { font-size: .95rem; font-weight: 500; }
.setting-hint { color: var(--secondary-text-color); font-size: .8rem; line-height: 1.45; }
.setting[data-disabled="true"] .setting-label { opacity: .6; }
.setting select {
  font: inherit;
  color: var(--primary-text-color);
  background: var(--card-background-color);
  border: 1px solid var(--divider-color);
  border-radius: 6px;
  padding: 8px;
  max-width: min(50vw,220px);
  min-width: 105px;
}
.setting ha-switch { display: block; flex-shrink: 0; }
.editor-section {
  border: 1px solid var(--divider-color);
  border-radius: 12px;
  overflow: hidden;
}
.editor-section-toggle {
  display: flex;
  align-items: center;
  box-sizing: border-box;
  gap: 12px;
  width: 100%;
  min-height: 62px;
  padding: 12px;
  border: 0;
  background: var(--secondary-background-color);
  color: var(--primary-text-color);
  text-align: start;
  cursor: pointer;
  font: inherit;
}
.editor-section-toggle > ha-icon:first-child { color: var(--secondary-text-color); }
.editor-section-toggle > ha-icon:last-child {
  color: var(--secondary-text-color);
  transition: transform .15s ease;
}
.editor-section-toggle[aria-expanded="true"] > ha-icon:last-child { transform: rotate(180deg); }
.editor-section-copy { display: grid; flex: 1; min-width: 0; gap: 3px; }
.editor-section-title { font-size: .95rem; font-weight: 600; }
.editor-section-hint { color: var(--secondary-text-color); font-size: .8rem; line-height: 1.35; }
.editor-section-content { display: grid; gap: 15px; padding: 14px; }
.editor-section-content[hidden] { display: none; }
.editor-soon-note {
  margin: 0;
  color: var(--secondary-text-color);
  font-size: .82rem;
  line-height: 1.45;
}
@media(max-width: 420px) {
  .setting { gap: 8px; }
  .setting select { max-width: 145px; }
  .editor-section-toggle { gap: 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .editor-section-toggle > ha-icon:last-child { transition: none; }
}
`;
