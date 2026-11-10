/** Ordered Salah Timetable styles: dashboard section. */
export const DASHBOARD_CSS = `/* HaCasa-inspired translucent surfaces, without external assets or dependencies. */
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
/* With two visible countdowns, distribute content from the top, not across
   available height. Previous Jamaat previously inherited space-between, so
   the extra sunrise line under Next Salah moved every Jamaat row down. Only
   target paired panels: the enlarged single-panel grid remains untouched. */
.summary-shell .panels:not(.single-panel) > .prayer-panel {
  justify-content: flex-start;
}
/* A narrow two-column card may wrap "Previous Jamaat" while "Next Salah"
   remains on one line. Give both labels the same two-line space so the
   following prayer name, clock and published times keep their baselines. */
@container(max-width:28rem) {
  .summary-shell .panels:not(.single-panel) > .prayer-panel > .label {
    min-height: 2.5em;
  }
  /* The smaller elapsed suffix can wrap onto a second countdown line. Match
     the height on both sides so the Beginning/Jamaat divider stays level. */
  .summary-shell .panels:not(.single-panel) > .prayer-panel > .count {
    min-height: 2.36em;
  }
}
/* Once the paired panels stack, their rows no longer need synchronized
   heights. Remove the reserved lines so phones keep the compact spacing. */
@container(max-width:21rem) {
  .summary-shell .panels:not(.single-panel) > .prayer-panel > .label,
  .summary-shell .panels:not(.single-panel) > .prayer-panel > .count {
    min-height: 0;
  }
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

`;
