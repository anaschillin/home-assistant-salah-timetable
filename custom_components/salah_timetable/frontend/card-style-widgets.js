/** Ordered Salah Timetable styles: widgets section. */
export const WIDGET_CSS = `/* Keep standalone previews and dashboard Sections at their natural height. */
:host([data-standalone]) {
  display: block;
  height: fit-content;
  min-height: 0;
  align-self: start;
}
ha-card.standalone-widget {
  height: fit-content;
  align-self: start;
}
ha-card.standalone-widget,
ha-card.standalone-widget.has-mosque-background,
ha-card.standalone-widget .content,
ha-card.standalone-widget .content.kiosk {
  min-height: 0;
}
ha-card.standalone-widget .content {
  display: flow-root;
  height: auto;
  min-height: 0;
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  padding: 16px;
}
ha-card.standalone-widget .summary-shell,
ha-card.standalone-widget .timetable-shell {
  margin: 0;
}
ha-card.standalone-widget .standalone-content > h2 {
  margin: 0 0 12px;
  font-size: clamp(1rem, 2.5cqi, 1.18rem);
  line-height: 1.35;
}
ha-card.standalone-widget .standalone-content > h2:only-child { margin-bottom: 0; }
ha-card.standalone-widget .linked-mosque-name {
  color: var(--secondary-text-color);
  overflow-wrap: anywhere;
}
ha-card.standalone-widget .widget-mosque-control {
  margin: 0 0 12px;
  font-size: 1.08rem;
  line-height: 1.35;
}
.widget-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 12px;
  margin: 0 0 14px;
}
.widget-heading h2,
.widget-heading h3 { margin: 0; font-size: 1.08rem; line-height: 1.4; }
.widget-mosque-name {
  min-width: 0;
  color: var(--secondary-text-color);
  font-size: .85rem;
  overflow-wrap: anywhere;
}
.widget-panel,
.widget-health,
.widget-changes {
  box-sizing: border-box;
  min-width: 0;
  margin-block: 14px;
  padding: 16px;
  border: 1px solid var(--divider-color);
  border-radius: 16px;
  background: var(--ha-card-background,var(--card-background-color));
  color: var(--primary-text-color);
  overflow-wrap: anywhere;
}
.widget-panel > :first-child,
.widget-health > :first-child,
.widget-changes > :first-child { margin-top: 0; }
.widget-panel > :last-child,
.widget-health > :last-child,
.widget-changes > :last-child { margin-bottom: 0; }
.widget-panel h3,
.widget-health h3,
.widget-changes h3 { font-size: 1.05rem; line-height: 1.4; margin-block: 0 12px; }
.widget-change-row {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  gap: 6px 12px;
  align-items: baseline;
  padding-block: 12px;
  border-top: 1px solid var(--divider-color);
}
.widget-change-row > * { min-width: 0; }
.widget-change-times {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  align-items: start;
  gap: 8px 16px;
  line-height: 1.5;
  font-variant-numeric: tabular-nums;
}
.widget-change-times > * { min-width: 0; }
.widget-health-row { margin-block: 10px; line-height: 1.5; }
.widget-health-row > * { min-width: 0; }
.widget-status {
  display: inline-block;
  max-width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  padding: 3px 8px;
  font-size: .8rem;
  line-height: 1.4;
  background: var(--secondary-background-color);
  color: var(--primary-text-color);
}
.widget-status[data-status="incomplete"],
.widget-status[data-status="unavailable"] { border-color: var(--warning-color,#a56b00); }
.widget-panel a,
.widget-health a { color: var(--primary-color); text-underline-offset: 3px; }
.widget-panel a:focus-visible,
.widget-health a:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
.arrangement-grid {
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 16px;
  width: 100%;
  min-width: 0;
  align-items: stretch;
}
.arrangement-section {
  container-type: inline-size;
  min-width: 0;
  box-sizing: border-box;
}
.arrangement-section[data-width="full"] { grid-column: 1 / -1; }
.arrangement-section[data-width="half"] { grid-column: auto; }
.arrangement-section > .summary-shell,
.arrangement-section > .timetable-shell,
.arrangement-section > .widget-panel,
.arrangement-section > .widget-health,
.arrangement-section > .widget-changes { margin: 0; height: 100%; box-sizing: border-box; }
.content.custom-arrangement { display: block; }
.content.custom-arrangement > .arrangement-grid { margin-block: 14px; }
.content.custom-arrangement.kiosk { display: block; }
.content.custom-arrangement.kiosk .summary-shell {
  min-height: 0;
  display: block;
}
.content.custom-arrangement.kiosk .header { grid-template-columns: minmax(0,1fr); }
.content.custom-arrangement.kiosk > .kiosk-footer { margin-top: 16px; }
.arrangement-toolbar {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  margin-block: 0 10px;
}
.arrangement-toolbar > .kiosk-fullscreen {
  position: static;
  inset: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  padding: 8px;
}
.arrangement-toolbar > .kiosk-fullscreen ha-icon { width: 20px; height: 20px; --mdc-icon-size: 20px; }
.arrangement-section .kiosk-clock { display: grid; gap: 6px; text-align: center; }
.arrangement-section .kiosk-clock-label { color: var(--secondary-text-color); font-size: .85rem; }
.arrangement-section .kiosk-clock-value {
  display: block;
  font-variant-numeric: tabular-nums;
  font-size: clamp(1.8rem,12cqi,4rem);
  line-height: 1.15;
}
@container(max-width:38rem) {
  .arrangement-grid { grid-template-columns: minmax(0,1fr); }
  .arrangement-section[data-width="half"] { grid-column: 1; }
}
@container(max-width:22rem) {
  .widget-panel,.widget-health,.widget-changes { padding: 12px; }
  .widget-change-row { grid-template-columns: minmax(0,1fr); }
  .widget-change-row > .widget-status { justify-self: start; }
}
@media (prefers-contrast: more), (prefers-reduced-transparency: reduce) {
  .widget-panel,.widget-health,.widget-changes {
    background: var(--card-background-color);
    border-color: var(--primary-text-color);
  }
}

/* Keep the paired countdown layout intact. Single summaries use their own
   available width, including when placed in a half-width arrangement section. */
.content .summary-shell .panels.single-panel {
  container: solo-countdown / inline-size;
  grid-template-columns: minmax(0,1fr);
  justify-items: center;
}
.content .summary-shell .panels.single-panel > .prayer-panel[data-panel] {
  display: grid;
  grid-template-areas: "heading heading" "name clock" "times times";
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: clamp(10px,3cqi,24px) clamp(8px,4cqi,42px);
  position: static;
  box-sizing: border-box;
  width: 100%;
  max-width: 68rem;
  padding: 0;
}
.content .summary-shell .panels.single-panel > .prayer-panel > .label {
  grid-area: heading;
  justify-content: center;
  margin: 0;
  text-align: center;
  font-size: clamp(.72rem,3cqi,1rem);
}
.content .summary-shell .panels.single-panel > .prayer-panel > .event {
  grid-area: name;
  min-width: 0;
  font-size: clamp(1.15rem,7.6cqi,1.875rem);
  font-weight: 750;
  line-height: 1.12;
}
.content .summary-shell .panels.single-panel > .prayer-panel > .count {
  grid-area: clock;
  min-width: 0;
  max-width: 60cqi;
  margin: 0;
  color: var(--primary-color);
  text-align: end;
  font-size: clamp(1.6rem,11.4cqi,2.75rem);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.035em;
  line-height: 1.06;
  overflow-wrap: anywhere;
}
.content .summary-shell .panels.single-panel > .prayer-panel > .fajr-sunrise {
  grid-column: 1 / -1;
  margin: 0;
}
.content .summary-shell .panels.single-panel > .prayer-panel > .panel-silhouette {
  inset-inline-end: auto;
  right: 0;
  inset-block-start: 0;
  opacity: .055;
}
.content .summary-shell .panels.single-panel > .prayer-panel > .prayer-times {
  grid-area: times;
  container-type: inline-size;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: clamp(10px,3cqi,28px) 8px;
  box-sizing: border-box;
  min-width: 0;
  margin: 0;
  padding: clamp(12px,4.6cqi,32px);
  border: 0;
  border-radius: clamp(12px,3.6cqi,20px);
  background: color-mix(in srgb,var(--primary-text-color) 9%,transparent);
}
.content .summary-shell .panels.single-panel > .prayer-panel .prayer-time {
  display: grid;
  align-content: start;
  gap: clamp(4px,2.5cqi,14px);
  text-align: start;
}
.content .summary-shell .panels.single-panel > .prayer-panel .prayer-time:nth-child(2) {
  text-align: end;
}
.content .summary-shell .panels.single-panel > .prayer-panel .prayer-time .label {
  font-size: clamp(.65rem,3.65cqi,1rem);
  line-height: 1.2;
  margin: 0;
}
.content .summary-shell .panels.single-panel > .prayer-panel .prayer-time .absolute {
  font-size: clamp(1.3rem,9.3cqi,2rem);
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
}
.timeline-strip {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: auto minmax(0,1fr) auto minmax(0,1fr) auto;
  align-items: center;
  gap: clamp(5px,2.8cqi,14px);
  font-size: clamp(.7rem,3.7cqi,1.125rem);
  font-weight: 700;
  text-align: center;
}
.timeline-caption {
  max-width: 17ch;
  overflow-wrap: anywhere;
}
.timeline-start,.timeline-end {
  box-sizing: border-box;
  width: clamp(10px,4.8cqi,20px);
  aspect-ratio: 1;
  border: clamp(2px,.75cqi,3px) solid var(--primary-color);
  border-radius: 50%;
}
.timeline-start,.timeline-strip.is-complete .timeline-end {
  background: var(--primary-color);
}
.timeline-line {
  height: clamp(2px,.75cqi,3px);
  background: color-mix(in srgb,var(--primary-text-color) 40%,transparent);
}
.timeline-line::before {
  content: "";
  display: block;
  width: var(--timeline-first-fill,0%);
  height: 100%;
  background: var(--primary-color);
}
.timeline-caption + .timeline-line::before { width: var(--timeline-second-fill,0%); }

@container solo-countdown (max-width: 18rem) {
  .content .summary-shell .panels.single-panel > .prayer-panel[data-panel] {
    grid-template-areas: "heading" "name" "clock" "times";
    grid-template-columns: minmax(0,1fr);
    text-align: center;
  }
  .content .summary-shell .panels.single-panel > .prayer-panel > .count {
    max-width: 100%;
    text-align: center;
  }
}
@container solo-countdown (min-width: 46rem) {
  .content .summary-shell .panels.single-panel > .prayer-panel[data-panel] {
    grid-template-areas: "heading heading" "name times" "clock times";
    grid-template-columns: minmax(0,1fr) minmax(0,1fr);
  }
  .content .summary-shell .panels.single-panel > .prayer-panel > .event {
    align-self: end;
    font-size: clamp(2rem,6.2cqi,3.5rem);
  }
  .content .summary-shell .panels.single-panel > .prayer-panel > .count {
    align-self: start;
    max-width: none;
    text-align: start;
    font-size: clamp(3.2rem,10.1cqi,5.9rem);
  }
  .content .summary-shell .panels.single-panel > .prayer-panel .prayer-time .absolute {
    font-size: clamp(2rem,17cqi,4rem);
  }
}
.content .summary-shell .panels.single-panel > .prayer-panel .prayer-times[data-time-format="12h"] .absolute {
  font-size: clamp(1rem,10cqi,2.55rem);
}

.content.single-countdown:not(.kiosk) > .summary-shell {
  padding: clamp(16px,4.35cqi,32px);
  border-radius: clamp(18px,4.35cqi,28px);
}
.content.compact.single-countdown:not(.kiosk) .header.has-month-action h2 {
  display: flex;
  align-items: center;
  min-height: clamp(44px,5.1cqi,52px);
  padding-inline-end: clamp(92px,12cqi,122px);
}
.content.single-countdown .card-actions-menu .card-more-toggle {
  min-height: clamp(44px,5.1cqi,52px);
  padding-inline: clamp(9px,1.6cqi,18px);
  border-radius: 12px;
  font-weight: 700;
}
.content.single-countdown .timetable-shell:has(.date-tabs) {
  border-radius: clamp(18px,4.35cqi,28px);
}
.content.single-countdown .date-tabs .date-tab {
  min-height: clamp(44px,5.5cqi,56px);
  border-radius: clamp(10px,1.55cqi,16px);
}
.content.single-countdown .date-tabs .date-tab[aria-pressed="true"] {
  background: #0b7fa8;
  color: #fff;
}
.content.single-countdown [data-role="timezone-note"] {
  color: var(--primary-text-color);
  font-size: clamp(.72rem,1.36cqi,.875rem);
}

`;
