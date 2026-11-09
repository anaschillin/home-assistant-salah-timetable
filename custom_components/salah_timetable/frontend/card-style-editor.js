/** Ordered Salah Timetable styles: editor section. */
export const EDITOR_CSS_PART = `
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
.setting[hidden] { display: none; }
.group-name-setting { grid-template-columns: minmax(0,1fr); gap: 6px; }
.group-sync-setting { border-top: 1px solid var(--divider-color); padding-top: 12px; }
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

/* The arrangement editor lives in the existing editor shadow root. */
.editor-tabs,
.widget-editor-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-block: 8px 14px; }
.editor-tabs[hidden],
.widget-editor-tabs[hidden],
.form[hidden],
[role="tabpanel"][hidden] { display: none; }
.editor-tabs button,
.widget-editor-tabs button {
  min-height: 44px;
  padding: 8px 16px;
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  color: var(--primary-text-color);
  background: var(--card-background-color);
  font: inherit;
  cursor: pointer;
}
.editor-tabs button[aria-selected="true"],
.widget-editor-tabs button[aria-selected="true"] { border-color: var(--primary-color); color: var(--primary-color); }
.layout-editor { display: grid; gap: 14px; min-width: 0; color: var(--primary-text-color); }
.layout-editor[hidden] { display: none; }
.layout-editor h3 { margin: 0; font-size: 1rem; }
.layout-toolbar { display: flex; flex-wrap: wrap; align-items: end; gap: 10px; }
.layout-toolbar label { display: grid; gap: 5px; min-width: 0; }
.layout-editor select,
.layout-editor button,
.layout-preview-controls button {
  box-sizing: border-box;
  min-height: 44px;
  max-width: 100%;
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  padding: 8px;
  font: inherit;
  color: var(--primary-text-color);
  background: var(--card-background-color);
}
.layout-editor button { cursor: pointer; }
.layout-editor button:disabled { opacity: .4; cursor: default; }
.layout-editor input { accent-color: var(--primary-color); }
.layout-editor button:focus-visible,
.layout-editor select:focus-visible,
.layout-editor input:focus-visible,
.editor-tabs button:focus-visible,
.widget-editor-tabs button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.layout-sections { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; min-width: 0; }
.layout-section-row {
  display: grid;
  grid-template-columns: 44px minmax(0,1fr) minmax(100px,140px) 44px 44px;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--divider-color);
  border-radius: 10px;
  background: var(--secondary-background-color);
}
.layout-section-row[aria-grabbed="true"] { outline: 2px solid var(--primary-color); }
.layout-section-label { display: flex; align-items: center; gap: 8px; min-width: 0; overflow-wrap: anywhere; line-height: 1.35; }
.layout-section-label input { flex-shrink: 0; }
.layout-section-row .layout-drag,
.layout-section-row .layout-move { display: grid; place-items: center; width: 44px; padding: 5px; }
.layout-section-row .layout-drag { cursor: grab; user-select: none; touch-action: none; }
.layout-section-row .layout-drag:active { cursor: grabbing; }
.layout-section-row .layout-width { width: 100%; min-width: 0; font-size: .85rem; }
.layout-section-row ha-icon { --mdc-icon-size: 20px; width: 20px; height: 20px; }
.layout-preview-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.layout-preview-controls button[aria-pressed="true"] { color: var(--primary-color); border-color: var(--primary-color); }
.layout-preview-frame {
  position: relative;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--divider-color);
  border-radius: 12px;
  background: var(--primary-background-color,var(--card-background-color));
}
.layout-preview-content {
  box-sizing: border-box;
  transform-origin: top left;
  padding: 8px;
}
:host([dir="rtl"]) .layout-preview-content { transform-origin: top right; }
.layout-preview-note { margin: 0; font-size: .82rem; line-height: 1.45; color: var(--secondary-text-color); }
.layout-editor .help { margin: 0; }
.widget-group-setting { display: grid; gap: 5px; }
.widget-group-setting input {
  box-sizing: border-box;
  width: 100%;
  min-height: 44px;
  padding: 8px;
  border: 1px solid var(--divider-color);
  border-radius: 8px;
  font: inherit;
  color: var(--primary-text-color);
  background: var(--card-background-color);
}
.widget-group-setting input:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
@container(max-width:32rem) {
  .layout-section-row { grid-template-columns: 44px minmax(0,1fr) 44px 44px; }
  .layout-section-row .layout-width { grid-column: 2 / -1; grid-row: 2; }
  .layout-section-row .layout-drag { grid-column: 1; grid-row: 1; }
  .layout-section-row .layout-section-label { grid-column: 2; grid-row: 1; }
  .layout-section-row .layout-move { grid-row: 1; }
}
`;
