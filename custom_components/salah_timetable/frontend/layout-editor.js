/** Per-card arrangement controls and an isolated preview of the actual card. */
import {SECTIONS, applyPreset, normalizeArrangement, resetArrangement, sectionVisible} from "./widget-utils.js?v=3.6.0";
import {widgetTr} from "./widget-i18n.js?v=3.6.0";

const PRESETS = ["countdown", "balanced", "timetable_first", "ramadan", "wall"];
const DEVICES = {phone: 360, tablet: 768, desktop: 1280};

function node(tag, className) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  return element;
}

function positions(config) {
  return normalizeArrangement(config.arrangement)?.sections
    || SECTIONS.map(({id, width}) => ({id, width}));
}

function arrangedConfig(config, arrangement) {
  const result = {...config, arrangement};
  // Explicit layouts lift Compact's section gates. Preserve the effective
  // visibility when the first width/order edit creates that explicit layout.
  if (!config.arrangement) {
    for (const {id, show} of SECTIONS) result[show] = sectionVisible(config, id);
  }
  return result;
}

/** onChange receives a complete config. Call dispose before replacing this root. */
export function buildLayoutEditor({config, hass, ui, onChange}) {
  let state = {config, hass, ui};
  let device = "phone";
  let dragged = null;
  let renderedOrder = "";
  let previewKey = "";
  let disposed = false;
  const rows = new Map();
  const root = node("div", "layout-editor");
  const toolbar = node("div", "layout-toolbar");
  const presetLabel = node("label");
  const presetText = node("span");
  const preset = node("select");
  preset.setAttribute("data-layout-preset", "");
  const presetPlaceholder = node("option");
  presetPlaceholder.value = "";
  presetPlaceholder.disabled = true;
  preset.append(presetPlaceholder);
  const presetOptions = PRESETS.map(value => {
    const option = node("option");
    option.value = value;
    preset.append(option);
    return {value, option};
  });
  presetLabel.append(presetText, preset);
  const reset = node("button");
  reset.type = "button";
  reset.setAttribute("data-layout-reset", "");
  toolbar.append(presetLabel, reset);
  const sectionHeading = node("h3");
  const sections = node("ol", "layout-sections");
  const previewHeading = node("h3");
  const previewControls = node("label", "layout-preview-controls");
  const deviceText = node("span");
  const deviceSelect = node("select");
  deviceSelect.setAttribute("data-layout-device", "");
  const deviceOptions = Object.entries(DEVICES).map(([value, width]) => {
    const option = node("option");
    option.value = value;
    deviceSelect.append(option);
    return {value, width, option};
  });
  previewControls.append(deviceText, deviceSelect);
  const previewNote = node("p", "layout-preview-note");
  const frame = node("div", "layout-preview-frame");
  frame.setAttribute("data-layout-preview-frame", "");
  frame.style.position = "relative";
  const previewContent = node("div", "layout-preview-content");
  previewContent.style.position = "absolute";
  previewContent.style.insetInlineStart = "0";
  previewContent.style.top = "0";
  const previewCard = document.createElement("salah-timetable-card");
  previewCard.setAttribute("data-layout-preview-card", "");
  // Set preview before config/hass so a named group can never be joined briefly.
  previewCard.preview = true;
  previewCard.style.width = "100%";
  previewContent.append(previewCard);
  frame.append(previewContent);
  root.append(toolbar, sectionHeading, sections, previewHeading,
    previewControls, previewNote, frame);

  function measurePreview() {
    if (disposed) return;
    const width = DEVICES[device];
    previewContent.style.width = `${width}px`;
    const available = frame.clientWidth || width;
    const scale = Math.min(1, available / width);
    previewContent.style.transform = `scale(${scale})`;
    const height = Math.max(previewContent.scrollHeight || 0, previewContent.offsetHeight || 0);
    frame.style.height = `${Math.ceil(height * scale)}px`;
  }

  function emit(next) {
    root.refresh({config: next});
    onChange(next);
  }

  function changeSection(id, patch) {
    const arrangement = {sections: positions(state.config).map(section => ({...section}))};
    if (patch.width) arrangement.sections.find(section => section.id === id).width = patch.width;
    const next = arrangedConfig(state.config, arrangement);
    if (patch.visible !== undefined) next[SECTIONS.find(section => section.id === id).show] = patch.visible;
    emit(next);
  }

  function reorder(source, destination) {
    const ordered = positions(state.config).map(section => ({...section}));
    const from = ordered.findIndex(section => section.id === source);
    const to = ordered.findIndex(section => section.id === destination);
    if (from < 0 || to < 0 || from === to) return;
    ordered.splice(to, 0, ordered.splice(from, 1)[0]);
    emit(arrangedConfig(state.config, {sections: ordered}));
  }

  function makeRow(id) {
    const row = node("li", "layout-section-row");
    row.setAttribute("data-layout-section", id);
    const drag = node("button", "layout-drag");
    drag.type = "button";
    drag.draggable = true;
    drag.setAttribute("data-layout-action", "drag");
    const grip = node("ha-icon");
    grip.setAttribute("icon", "mdi:drag-vertical");
    grip.setAttribute("aria-hidden", "true");
    drag.append(grip);
    drag.addEventListener("dragstart", event => {
      dragged = id;
      event.dataTransfer?.setData("application/x-salah-layout-section", id);
      event.dataTransfer?.setData("text/plain", id);
      if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
    });
    drag.addEventListener("dragend", () => { dragged = null; });
    row.addEventListener("dragover", event => {
      if (!dragged || dragged === id) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
    });
    row.addEventListener("drop", event => {
      if (!dragged) return;
      event.preventDefault();
      const source = dragged;
      dragged = null;
      reorder(source, id);
    });
    const label = node("label", "layout-section-label");
    const visible = node("input");
    visible.type = "checkbox";
    visible.setAttribute("data-layout-action", "visible");
    const name = node("span");
    label.append(visible, name);
    visible.addEventListener("change", () => changeSection(id, {visible: visible.checked}));
    const width = node("select", "layout-width");
    width.setAttribute("data-layout-action", "width");
    const full = node("option"); full.value = "full";
    const half = node("option"); half.value = "half";
    width.append(full, half);
    width.addEventListener("change", () => changeSection(id, {width: width.value}));
    const move = (delta, action) => {
      const button = node("button", "layout-move");
      button.type = "button";
      button.setAttribute("data-layout-action", action);
      const icon = node("ha-icon");
      icon.setAttribute("icon", delta < 0 ? "mdi:chevron-up" : "mdi:chevron-down");
      icon.setAttribute("aria-hidden", "true");
      button.append(icon);
      button.addEventListener("click", () => {
        const ordered = positions(state.config);
        const index = ordered.findIndex(section => section.id === id);
        if (ordered[index + delta]) reorder(id, ordered[index + delta].id);
      });
      return button;
    };
    const up = move(-1, "up"), down = move(1, "down");
    row.append(drag, label, width, up, down);
    return {row, drag, visible, name, width, full, half, up, down};
  }

  preset.addEventListener("change", () => {
    if (PRESETS.includes(preset.value)) emit(applyPreset(state.config, preset.value));
  });
  reset.addEventListener("click", () => emit(resetArrangement(state.config)));
  deviceSelect.addEventListener("change", () => {
    if (!Object.prototype.hasOwnProperty.call(DEVICES, deviceSelect.value)) return;
    device = deviceSelect.value;
    measurePreview();
  });

  root.refresh = update => {
    if (disposed) return;
    state = {...state, ...update};
    const translate = (key, params) => widgetTr(state.ui, key, params);
    root.setAttribute("dir", state.ui?.dir || "ltr");
    presetText.textContent = translate("layout.preset");
    presetPlaceholder.textContent = translate("layout.preset");
    for (const {value, option} of presetOptions) option.textContent = translate(`preset.${value}`);
    preset.value = "";
    reset.textContent = translate("layout.reset");
    sectionHeading.textContent = translate("layout.sections");
    previewHeading.textContent = translate("layout.preview");
    deviceText.textContent = translate("layout.preview");
    for (const {value, width, option} of deviceOptions) option.textContent = `${translate(`layout.device.${value}`)} (${width}px)`;
    deviceSelect.value = device;
    previewNote.textContent = translate("layout.preview_note");
    const ordered = positions(state.config);
    const orderKey = ordered.map(section => section.id).join(",");
    let restoreFocus;
    if (orderKey !== renderedOrder) {
      // Move the existing nodes: focused controls and native drag state survive.
      for (const {id} of ordered) {
        if (!rows.has(id)) rows.set(id, makeRow(id));
      }
      const active = root.getRootNode?.().activeElement;
      const focusedRow = active?.closest?.("[data-layout-section]")?.getAttribute("data-layout-section");
      const focusedAction = active?.getAttribute?.("data-layout-action");
      sections.replaceChildren(...ordered.map(({id}) => rows.get(id).row));
      renderedOrder = orderKey;
      if (focusedRow && rows.has(focusedRow)) restoreFocus = {id: focusedRow, action: focusedAction};
    }
    ordered.forEach(({id, width}, index) => {
      const controls = rows.get(id);
      const name = translate(`section.${id}`);
      controls.name.textContent = name;
      controls.visible.checked = sectionVisible(state.config, id);
      controls.row.setAttribute("data-visible", String(controls.visible.checked));
      controls.visible.setAttribute("aria-label", translate("layout.visible", {name}));
      controls.drag.setAttribute("aria-label", translate("layout.drag", {name}));
      controls.drag.title = translate("layout.drag", {name});
      controls.width.setAttribute("aria-label", translate("layout.width", {name}));
      controls.full.textContent = translate("layout.full");
      controls.half.textContent = translate("layout.half");
      controls.width.value = width;
      controls.up.disabled = index === 0;
      controls.down.disabled = index === ordered.length - 1;
      for (const [action, control] of [["move_up", controls.up], ["move_down", controls.down]]) {
        control.setAttribute("aria-label", translate(`layout.${action}`, {name}));
        control.title = translate(`layout.${action}`, {name});
      }
    });
    if (restoreFocus) {
      const controls = rows.get(restoreFocus.id);
      const target = controls[restoreFocus.action];
      (target && !target.disabled ? target : controls.drag).focus?.({preventScroll: true});
    }
    const nextPreviewKey = JSON.stringify(state.config);
    if (nextPreviewKey !== previewKey) {
      const {selection_group: _group, ...previewConfig} = state.config;
      previewCard.setConfig({...previewConfig, type: "custom:salah-timetable-card"});
      previewKey = nextPreviewKey;
    }
    previewCard.hass = state.hass;
    measurePreview();
  };
  const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measurePreview);
  observer?.observe(frame);
  observer?.observe(previewContent);
  root.dispose = () => {
    disposed = true;
    observer?.disconnect();
  };
  root.refresh({});
  return root;
}
