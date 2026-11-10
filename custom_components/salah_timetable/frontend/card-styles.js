/** Ordered theme-aware styles for the dashboard and configuration editor. */
import {FOUNDATION_CSS} from "./card-style-foundation.js?v=3.6.1";
import {DASHBOARD_CSS} from "./card-style-dashboard.js?v=3.6.1";
import {KIOSK_CSS} from "./card-style-kiosk.js?v=3.6.1";
import {WIDGET_CSS} from "./card-style-widgets.js?v=3.6.1";
import {EDITOR_CSS_PART} from "./card-style-editor.js?v=3.6.1";

// Order matters: later declarations override earlier layout and theme rules.
export const CARD_CSS = FOUNDATION_CSS + DASHBOARD_CSS + KIOSK_CSS + WIDGET_CSS;
export const EDITOR_CSS = EDITOR_CSS_PART;
