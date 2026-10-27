/** Theme-aware card styles. Keep responsive and preference overrides in cascade order. */
export const CARD_CSS = `
.date-tabs {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:6px;
  padding:4px;
  background:var(--secondary-background-color);
  border-radius:12px;
  margin:0 0 16px
}
.date-tab {
  border:0;
  border-radius:9px;
  padding:10px 5px;
  font:inherit;
  font-weight:600;
  background:transparent;
  color:var(--secondary-text-color);
  cursor:pointer
}
.date-tab[aria-pressed="true"] {
  background:var(--primary-color);
  color:var(--text-primary-color,#fff)
}
.date-tab:focus-visible {
  outline:2px solid var(--primary-color);
  outline-offset:2px
}
.selected-date {
  font-size:.9rem;
  font-weight:600;
  color:var(--secondary-text-color);
  margin-bottom:12px
}
.mosque-tabs {
  display:flex;
  gap:6px;
  overflow-x:auto;
  margin:0 0 16px;
  padding:4px;
  border-radius:12px;
  background:var(--secondary-background-color)
}
.mosque-tab {
  flex:1 0 auto;
  border:0;
  border-radius:9px;
  padding:10px 14px;
  font:inherit;
  font-weight:600;
  background:transparent;
  color:var(--secondary-text-color);
  cursor:pointer
}
.mosque-tab[aria-pressed="true"] {
  background:var(--primary-color);
  color:var(--text-primary-color,#fff)
}
.mosque-tab:focus-visible {
  outline:2px solid var(--primary-color);
  outline-offset:2px
}
.prayer-panel {
  gap:8px
}
.prayer-panel .event {
  min-height:1.7em
}
.prayer-panel .count {
  margin:4px 0 8px
}
.prayer-times {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
  margin-top:auto;
  padding-top:12px;
  border-top:1px solid var(--divider-color)
}
.prayer-time {
  min-width:0
}
.prayer-time .label {
  margin:0 0 5px
}
.prayer-time .absolute {
  font-size:1.1rem;
  font-weight:700;
  color:var(--primary-text-color);
  margin:0
}
.prayer-panel[data-panel="jamaat"] {
  justify-content:space-between
}
.fajr-sunrise {
  margin-top:5px
}
:host {
  display:block;
  container-type:inline-size;
  color:var(--primary-text-color);
  font-family:var(--paper-font-body1_-_font-family,inherit)
}
ha-card {
  display:block;
  overflow:hidden;
  background:var(--ha-card-background,var(--card-background-color));
  border-radius:var(--ha-card-border-radius,12px)
}
.content {
  padding:20px
}
.header {
  display:flex;
  gap:12px;
  align-items:baseline;
  justify-content:space-between;
  flex-wrap:wrap
}
h2 {
  font-size:1.35rem;
  margin:0;
  overflow-wrap:anywhere
}
.date {
  color:var(--secondary-text-color);
  font-size:.9rem
}
.panels {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
  margin:18px 0
}
.panel {
  border-radius:10px;
  padding:14px;
  background:var(--secondary-background-color);
  min-width:0
}
.label {
  color:var(--secondary-text-color);
  font-size:.83rem;
  margin-bottom:5px
}
.event {
  font-weight:600;
  font-size:1.05rem
}
.count {
  font-variant-numeric:tabular-nums;
  font-size:clamp(1.6rem,6cqi,2.2rem);
  color:var(--primary-color);
  margin-top:7px;
  overflow-wrap:anywhere
}
.absolute {
  color:var(--secondary-text-color);
  font-size:.85rem;
  margin-top:5px
}
.table-scroll {
  max-width:100%;
  overflow-x:auto
}
thead th {
  overflow-wrap:anywhere
}
table {
  width:100%;
  border-collapse:collapse;
  font-size:.97rem
}
th,td {
  padding:10px 6px;
  border-bottom:1px solid var(--divider-color);
  text-align:end;
  font-variant-numeric:tabular-nums
}
th:first-child,td:first-child {
  text-align:start
}
th {
  color:var(--secondary-text-color);
  font-size:.83rem;
  font-weight:500
}
tr:last-child td,tr:last-child th {
  border-bottom:0
}
.ramadan {
  border-top:1px solid var(--divider-color);
  margin-top:14px;
  padding-top:14px
}
.ramadan h3 {
  font-size:1rem;
  margin:0 0 12px
}
.ramadan-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px
}
.ramadan .count {
  font-size:1.1rem
}
.note {
  color:var(--secondary-text-color);
  font-size:.83rem;
  margin:12px 0 0
}
.empty {
  padding:22px;
  color:var(--secondary-text-color);
  line-height:1.5
}
.disconnected {
  color:var(--error-color);
  font-size:.85rem;
  margin:8px 0
}
.sr-only {
  position:absolute;
  width:1px;
  height:1px;
  padding:0;
  margin:-1px;
  overflow:hidden;
  clip:rect(0,0,0,0);
  white-space:nowrap;
  border:0
}
@media(max-width:420px) {
  .content {
    padding:14px
  }
  .panels {
    gap:8px
  }
  .panel {
    padding:10px
  }
  .count {
    font-size:1.6rem
  }
  .ramadan-grid {
    grid-template-columns:1fr 1fr
  }
  .ramadan-grid>:last-child {
    grid-column:1/-1
  }
  th,td {
    padding:9px 3px;
    font-size:.9rem
  }
}
.progress-help {
  font-size:.72rem;
  color:var(--secondary-text-color);
  margin-top:5px
}
.scroll-help {
  display:none;
  font-size:.75rem
}
.event,.absolute,.date,.label {
  overflow-wrap:anywhere
}
bdi {
  unicode-bidi:isolate
}
.prayer-labels {
  display:inline-flex;
  flex-wrap:wrap;
  gap:.3em;
  align-items:baseline
}
.prayer-labels bdi {
  overflow-wrap:anywhere
}
.label-separator {
  font-weight:400;
  color:var(--secondary-text-color)
}
progress::-webkit-progress-bar {
  background:var(--divider-color)
}
progress::-webkit-progress-value {
  background:var(--primary-color)
}
progress::-moz-progress-bar {
  background:var(--primary-color)
}
progress {
  display:block;
  width:100%;
  height:4px;
  margin-top:12px;
  border:0;
  accent-color:var(--primary-color)
}
.next-prayer {
  background:color-mix(in srgb,var(--primary-color) 12%,transparent)
}
.next-prayer th,.next-prayer td {
  font-weight:700;
  font-size:1.05em
}
.past-prayer {
  color:var(--secondary-text-color)
}
.congregation-time {
  white-space:nowrap
}
.hijri {
  flex-basis:100%
}
.compact {
  padding:12px
}
.compact th,.compact td {
  padding-top:6px;
  padding-bottom:6px
}
.compact .panel {
  padding:10px
}
.compact .count {
  font-size:1.6rem
}
table {
  table-layout:fixed;
  min-width:22rem
}
th:first-child {
  width:30%
}
.panels:has(>:only-child) {
  grid-template-columns:1fr
}
@container(max-width:26rem) {
  .scroll-help {
    display:block
  }
  .panels {
    grid-template-columns:1fr
  }
  .count {
    font-size:1.7rem
  }
  .ramadan-grid {
    grid-template-columns:1fr 1fr
  }
  .ramadan-grid>:last-child {
    grid-column:1/-1
  }
}
/* HaCasa-inspired translucent surfaces, without external assets or dependencies. */
ha-card {
  position:relative;
  isolation:isolate;
  background:var(--ha-card-background,var(--card-background-color));
}
ha-card::before {
  content:"";
  position:absolute;
  inset:0;
  z-index:-1;
  pointer-events:none;
  background:radial-gradient(ellipse at 95% 0%,color-mix(in srgb,var(--primary-color) 12%,transparent),transparent 55%)
}
.panel {
  background:color-mix(in srgb,var(--secondary-background-color) 82%,transparent);
  box-shadow:0 5px 18px rgba(0,0,0,.055);
  backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px)
}
.panel[data-panel="salah"] {
  background:color-mix(in srgb,var(--primary-color) 13%,var(--ha-card-background,var(--card-background-color)))
}
.table-scroll {
  background:color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 92%,transparent)
}
@media(prefers-contrast:more) {
  .panel,.panel[data-panel="salah"],.table-scroll {
    background:var(--card-background-color);
    border:2px solid var(--primary-text-color);
    box-shadow:none
  }
}
@media(prefers-reduced-transparency:reduce) {
  .panel,.table-scroll {
    backdrop-filter:none;
    -webkit-backdrop-filter:none;
    background:var(--secondary-background-color)
  }
}
/* Modern dashboard presentation: retain HA theme variables and accessible table semantics. */
ha-card {
  border:1px solid var(--divider-color);
  box-shadow:0 8px 28px rgba(0,0,0,.07)
}
.content {
  padding:clamp(14px,3cqi,24px)
}
.header {
  align-items:flex-start;
  gap:6px 16px;
  margin-bottom:18px
}
.header h2 {
  font-size:clamp(1.25rem,3cqi,1.65rem);
  font-weight:700;
  letter-spacing:-.025em;
  flex-basis:100%
}
.date {
  font-size:.82rem
}
.hijri {
  flex-basis:auto;
  font-weight:600;
  color:var(--primary-text-color)
}
.panels {
  gap:12px;
  margin:0 0 22px
}
.panel {
  padding:clamp(14px,2.6cqi,20px);
  border:1px solid var(--divider-color);
  border-radius:16px;
  background:var(--secondary-background-color);
  display:flex;
  flex-direction:column;
  gap:4px
}
.panel[data-panel="salah"] {
  background:color-mix(in srgb,var(--primary-color) 9%,var(--ha-card-background,var(--card-background-color)));
  border-color:color-mix(in srgb,var(--primary-color) 22%,var(--divider-color))
}
.panel .label {
  font-size:.73rem;
  letter-spacing:.075em;
  text-transform:uppercase;
  font-weight:700
}
.panel .event {
  font-size:1.2rem
}
.panel .count {
  font-size:clamp(1.65rem,5.5cqi,2.65rem);
  font-weight:750;
  letter-spacing:-.045em;
  margin:4px 0
}
.panel .absolute {
  font-size:.88rem
}
.panel progress {
  height:6px;
  border-radius:99px;
  overflow:hidden;
  margin-top:10px
}
.progress-help {
  font-size:.72rem
}
.table-scroll {
  border:1px solid var(--divider-color);
  border-radius:14px;
  overflow-x:auto
}
table {
  min-width:0;
  table-layout:auto
}
thead {
  background:var(--secondary-background-color)
}
th,td {
  padding:12px 10px
}
thead th {
  font-size:.73rem;
  letter-spacing:.04em;
  text-transform:uppercase
}
tbody tr:not(:last-child) {
  border-bottom:1px solid var(--divider-color)
}
tbody tr th,tbody tr td {
  border-bottom:0
}
.next-prayer {
  background:color-mix(in srgb,var(--primary-color) 13%,transparent);
  box-shadow:inset 3px 0 var(--primary-color)
}
.next-prayer th,.next-prayer td {
  font-weight:700
}
.past-prayer {
  color:var(--secondary-text-color);
  opacity:1
}
.past-prayer th,.past-prayer td {
  color:inherit
}
.ramadan {
  margin-top:20px
}
.ramadan-grid>div {
  background:var(--secondary-background-color);
  border:1px solid var(--divider-color);
  padding:14px;
  border-radius:12px
}
.compact {
  padding:12px
}
.compact .panel {
  padding:12px
}
.compact .panel .count {
  font-size:1.65rem
}
@container(max-width:28rem) {
  .panels {
    grid-template-columns:1fr
  }
  .table-scroll {
    border:0;
    border-radius:0
  }
  table {
    width:100%;
    min-width:0;
    font-size:.86rem
  }
  th,td {
    padding:9px 4px
  }
  th:first-child {
    width:auto
  }
  .panel .count {
    font-size:2rem
  }
  .ramadan-grid {
    grid-template-columns:1fr 1fr
  }
}
@media(prefers-reduced-motion:no-preference) {
  .panel,.next-prayer {
    transition:background-color .2s ease,border-color .2s ease
  }
}
`;
