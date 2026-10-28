/** Theme-aware card styles. Keep responsive and preference overrides in cascade order. */
export const CARD_CSS = `
.background-credit { display: block; text-align: end; margin-top: 10px; font-size: .7rem; opacity: .75; }
.background-credit a { color: var(--secondary-text-color); text-decoration: underline; text-underline-offset: 2px; }
.background-credit a:focus-visible { outline: 2px solid var(--primary-color); }

/* The background has its own photo canvas. Its height is anchored to the
   full Today card so hiding countdowns does not re-zoom/re-centre the image.
   Clip the extended photo layer inside the card without changing card height. */
ha-card.has-mosque-background {
  background: var(--ha-card-background,var(--card-background-color));
}
ha-card.has-mosque-background::before {
  content: "";
  position: absolute;
  inset: 1px 1px auto;
  height: max(calc(100% - 2px),var(--mosque-photo-frame-height,100%));
  z-index: 0;
  pointer-events: none;
  background-image: linear-gradient(var(--mosque-overlay),var(--mosque-overlay)),var(--mosque-background-image);
  background-origin: padding-box;
  background-clip: padding-box;
  background-position: center,var(--mosque-background-position,center);
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
.date-tab,.mosque-tab {
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
.date-tab[aria-pressed="true"],.mosque-tab[aria-pressed="true"] {
  background: var(--primary-color);
  color: var(--text-primary-color,#fff);
}
.date-tab:focus-visible,.mosque-tab:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.selected-date {
  font-size: .9rem;
  font-weight: 600;
  color: var(--secondary-text-color);
  margin-bottom: 12px;
}
.mosque-tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  margin: 0 0 16px;
  padding: 4px;
  border-radius: 12px;
  background: var(--secondary-background-color);
}
.mosque-tab {
  flex: 1 0 auto;
  padding: 10px 14px;
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
/* Modern dashboard presentation: retain HA theme variables and accessible table semantics. */
ha-card {
  border: 1px solid var(--divider-color);
  box-shadow: 0 8px 28px rgba(0,0,0,.07);
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
  background: color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 92%,transparent);
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
  box-shadow: 0 14px 44px rgba(0,0,0,.13), inset 0 1px rgba(255,255,255,.05);
  border-color: color-mix(in srgb,var(--primary-color) 17%,var(--divider-color));
}
.content {
  box-sizing: border-box;
  width: 100%;
  max-width: 1160px;
  margin-inline: auto;
}
/* Only soften the photo through the card; keep the true glass blur on
   individual panels and concentrate the stronger blur at the image rim. */
ha-card.has-mosque-background .content {
  z-index: 1;
  background: color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 8%,transparent);
  backdrop-filter: blur(1px);
  -webkit-backdrop-filter: blur(1px);
}
/* Blur only the photograph at the rim, never the timetable or lettering. */
ha-card.has-mosque-background::after {
  content: "";
  position: absolute;
  inset: 1px 1px auto;
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
/* A single, evenly frosted surface provides contrast over the full-width
   mosque photo. Both live countdowns use exactly the same visual treatment:
   no second background, border, shadow or inset accent on either half. */
.summary-shell {
  min-width: 0;
  margin-bottom: 16px;
  padding: clamp(14px,2.4cqi,22px);
  border: 1px solid color-mix(in srgb,var(--primary-text-color) 15%,transparent);
  border-radius: 18px;
  overflow: hidden;
  isolation: isolate;
  background: color-mix(in srgb,var(--secondary-background-color) 94%,transparent);
  box-shadow: 0 12px 32px rgba(0,0,0,.16), inset 0 1px rgba(255,255,255,.10);
  backdrop-filter: blur(18px) saturate(115%);
  -webkit-backdrop-filter: blur(18px) saturate(115%);
}
.summary-shell .header {
  margin: 0;
}
.summary-shell .panels {
  grid-template-columns: repeat(2,minmax(0,1fr));
  align-items: stretch;
  margin: 14px 0 0;
  padding-top: 14px;
  gap: 0;
  border-top: 1px solid color-mix(in srgb,var(--primary-text-color) 14%,transparent);
}
/* Match specificity for Salah and Jamaat, including the earlier data-panel
   accent selector. Color is reserved for both clocks, not either background. */
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
.summary-shell .prayer-panel .panel-silhouette {
  opacity: .08;
}
@container(max-width:21rem) {
  .summary-shell .panels { grid-template-columns: 1fr; }
  .summary-shell .prayer-panel + .prayer-panel {
    border-inline-start: 0;
    border-block-start: 1px solid color-mix(in srgb,var(--primary-text-color) 14%,transparent);
  }
}
@media (prefers-contrast: more), (prefers-reduced-transparency: reduce) {
  .summary-shell {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    background: var(--secondary-background-color);
  }
}
@media (prefers-contrast: more) {
  .summary-shell {
    border: 2px solid var(--primary-text-color);
    box-shadow: none;
  }
  .summary-shell .panels,
  .summary-shell .prayer-panel + .prayer-panel,
  .summary-shell .prayer-panel .prayer-times {
    border-color: var(--primary-text-color);
  }
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

`;

/** Card configuration editor styles, scoped to its separate shadow root. */
export const EDITOR_CSS = `
:host {
  display: block;
}
.form {
  display: grid;
  gap: 16px;
  padding: 12px 0;
}
.help {
  color: var(--secondary-text-color);
  font-size: .9rem;
}
.error {
  color: var(--error-color);
}
.setting {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.setting select {
  font: inherit;
  color: var(--primary-text-color);
  background: var(--card-background-color);
  padding: 8px;
  max-width: 55%;
}
.setting span {
  overflow-wrap: anywhere;
}
.mosque-options {
  display: grid;
  gap: 8px;
}
.mosque-options[hidden] {
  display: none;
}
.mosque-options-heading {
  font-weight: 600;
}
.mosque-options-list {
  display: grid;
  gap: 8px;
}
.mosque-choice {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.mosque-choice input {
  accent-color: var(--primary-color);
}
.setting input:disabled {
  cursor: not-allowed;
  opacity: .55;
}
.title-field {
  display: grid;
  gap: 7px;
}
.title-field label {
  font: inherit;
  color: var(--primary-text-color);
}
.title-field input {
  box-sizing: border-box;
  width: 100%;
  padding: 12px;
  border: 1px solid var(--divider-color);
  border-radius: 4px;
  background: var(--card-background-color);
  color: var(--primary-text-color);
  font: inherit;
}
.title-field input:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}
@media(max-width: 420px) {
  .setting {
    gap: 8px;
  }
}
`;
