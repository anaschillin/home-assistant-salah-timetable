/** Shared DOM primitives and configuration validation for card and editor. */
import {normalizeConfig} from "./card-utils.js?v=3.6.0";
import {resolveUi} from "./card-i18n.js?v=3.6.0";
import {widgetTr} from "./widget-i18n.js?v=3.6.0";

export function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

export function direction(element, ui) {
  element.setAttribute("lang", ui.language);
  element.setAttribute("dir", ui.dir);
  return element;
}

export function normalizeForUi(config, hass) {
  try { return normalizeConfig(config); }
  catch (error) {
    if (!error.translationKey) throw error;
    throw new Error(widgetTr(resolveUi(config, hass), error.translationKey, error.params));
  }
}
