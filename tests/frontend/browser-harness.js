/** Real-browser fixture: native shadow DOM/CSS with small HA control stand-ins. */
import {SalahTimetableCard, SalahTimetableCardEditor} from "/custom_components/salah_timetable/frontend/salah-timetable-card.js?v=0.9.19";
import {resolveUi, tr} from "/custom_components/salah_timetable/frontend/card-i18n.js?v=0.9.19";
import {formatDate, formatHijriDate, hijriMonthInfo} from "/custom_components/salah_timetable/frontend/card-utils.js?v=0.9.19";

class Selector extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode: "open"}); this.select = document.createElement("select"); this.shadowRoot.append(this.select);
    this.select.addEventListener("change", () => this.dispatchEvent(new CustomEvent("value-changed", {detail: {value: this.value}, bubbles: true, composed: true})));
  }
  set hass(value) { this._hass = value; this._options(); }
  set selector(value) { this._selector = value; this._options(); }
  get value() { return this.select.value; }
  set value(value) { this._value = value; this.select.value = value; }
  _options() {
    const options = this._selector?.select?.options || (this._selector?.entity ? Object.keys(this._hass?.states || {}).map(value => ({value, label: value})) : []);
    this.select.replaceChildren(...options.map(value => { const option = document.createElement("option"); option.value = value.value; option.textContent = value.label; return option; }));
    this.select.value = this._value || "";
  }
}
if (!customElements.get("ha-selector")) customElements.define("ha-selector", Selector);

const query = new URLSearchParams(location.search);
const language = query.get("language") === "ar" ? "ar" : "en";
const bilingual = query.get("bilingual") === "true";
const width = window.innerWidth;
const checks = [];
function check(name, assertion) { if (!assertion) throw new Error(name); checks.push(name); }
function visibility(card) {
  const root = card.shadowRoot;
  const nodes = {
    show_hijri_date: root.querySelector(".hijri"),
    show_gregorian_date: root.querySelector(".gregorian"),
    show_salah_countdown: root.querySelector('[data-panel="salah"]'),
    show_jamaat_countdown: root.querySelector('[data-panel="jamaat"]'),
    show_ramadan_details: root.querySelector(".ramadan"),
    show_sehri_countdown: root.querySelector('[data-ramadan="sehri"] .count'),
    show_iftar_countdown: root.querySelector('[data-ramadan="iftar"] .count'),
    show_timezone_note: root.querySelector('[data-role="timezone-note"]'),
  };
  return Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, Boolean(node?.getClientRects().length)]));
}
function fits(card) {
  const root = card.shadowRoot;
  return card.getBoundingClientRect().width <= width + 1 && document.documentElement.scrollWidth <= width + 1 &&
    [".content", ".header", ".panels", ".ramadan", ".ramadan-grid", "h2", ".panel"].every(selector => [...root.querySelectorAll(selector)].every(element => element.scrollWidth <= element.clientWidth + 1));
}
const time = (hour, minute = 0) => `2026-10-21T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`;
const event = (timestamp, prayer) => ({timestamp, prayer, field: `${prayer}_jamaat`});
const prayers = [
  {key: "fajr", name: "Fajr", begin: time(4, 45), end: time(6, 30), jamaat: [time(5, 15)]},
  {key: "dhuhr", name: "Dhuhr", begin: time(11), jamaat: [time(11, 30)]},
  {key: "asr", name: "Asr", begin: time(14), jamaat: [time(14, 30)]},
  {key: "maghrib", name: "Maghrib", begin: time(16, 30), jamaat: [time(16, 33)]},
  {key: "isha", name: "Isha", begin: time(18), jamaat: [time(18, 30)]},
];
const data = {
  mosque_name: "Example Mosque", date: "2026-10-21", time_zone: "Europe/London", prayers, show_hijri_date: true,
  next_salah: {timestamp: time(4, 45), prayer: "fajr", field: "fajr_begin"},
  next_jamaat: event(time(5, 15), "fajr"), previous_jamaat: event("2026-10-20T18:30:00Z", "isha"), context_mode: "previous",
  beginning_events: prayers.map(prayer => ({timestamp: prayer.begin, prayer: prayer.key, field: `${prayer.key}_begin`})),
  jamaat_events: prayers.flatMap(prayer => prayer.jamaat.map(timestamp => event(timestamp, prayer.key))),
  ramadan: {active: true, sehri: time(4, 40), iftar: time(16, 30), taraweeh: null, taraweeh_text: "After Isha Jamaat"},
};
let serviceCalls = 0;
const hass = {states: {"sensor.example_prayer_timetable": {state: data.date, attributes: data}}, locale: {language: "en-GB"}, config: {time_zone: data.time_zone}, connection: {connected: true}, callService() { serviceCalls++; }};
const config = {entity: "sensor.example_prayer_timetable", detail_level: "detailed", language, bilingual_prayer_labels: bilingual, show_mosque_background: false};
const ui = resolveUi(config, hass);
const digits = value => new Intl.NumberFormat(ui.locale, {useGrouping: false, minimumIntegerDigits: 2}).format(value);
const zero = `${digits(0)}:${digits(0)}:${digits(0)}`;

try {
  const card = new SalahTimetableCard();
  const render = (patch = {}, now = time(4, 40)) => { card.setConfig({...config, ...patch}); card._render(Date.parse(now)); };
  card.setConfig(config); card.hass = hass; document.body.append(card); card._render(Date.parse(time(4, 40)));
  check("shadow DOM renders five prayer rows", card.shadowRoot.querySelectorAll("tbody tr").length === 5);
  render({show_mosque_background: true, mosque_background: "masjid-al-haram"});
  check("bundled mosque background resolves to local WebP", card.shadowRoot.querySelector("ha-card").style.getPropertyValue("--mosque-background-image").includes("/salah_timetable/backgrounds/masjid-al-haram.webp"));
  check("photo includes a photographer credit", card.shadowRoot.querySelector(".background-credit a")?.href.includes("unsplash.com/photos/"));
  const photoCard = card.shadowRoot.querySelector("ha-card");
  const photoStyle = getComputedStyle(photoCard);
  const viewingMinHeight = photoStyle.minHeight;
  check("photo fills the normal dashboard and edit preview shortens the canvas",
    Number.parseFloat(viewingMinHeight) > 0);
  card.preview = true;
  check("HA card editor preview no longer forces an entire viewport of height",
    card.hasAttribute("dashboard-editing") && getComputedStyle(photoCard).minHeight === "0px");
  card.preview = false;
  check("leaving dashboard edit restores the full viewport canvas",
    !card.hasAttribute("dashboard-editing") && getComputedStyle(photoCard).minHeight === viewingMinHeight);
  check("full-canvas card has no outer drop shadow", photoStyle.boxShadow === "none");
  const imageStyle = getComputedStyle(photoCard, "::before");
  check("unobscured photo stays inside themed borders at mobile/tablet widths",
    imageStyle.backgroundImage.includes("masjid-al-haram.webp") &&
    !imageStyle.backgroundImage.includes("linear-gradient") &&
    imageStyle.backgroundClip.split(",").every(value => value.trim() === "padding-box") &&
    imageStyle.backgroundOrigin.split(",").every(value => value.trim() === "padding-box") &&
    photoStyle.overflow === "hidden" &&
    photoStyle.borderTopWidth !== "0px" && photoStyle.borderBottomWidth !== "0px");
  const rimStyle = getComputedStyle(photoCard, "::after");
  const glassStyle = getComputedStyle(photoCard.querySelector(".content"));
  check("full-canvas background and centred inner glass content are applied",
    photoStyle.maxWidth === "none" &&
    imageStyle.backgroundSize.split(",").every(value => value.trim() === "cover") &&
    Math.abs(photoCard.getBoundingClientRect().width - card.getBoundingClientRect().width) <= 2 &&
    glassStyle.maxWidth === "1160px" &&
    glassStyle.marginLeft === glassStyle.marginRight &&
    rimStyle.filter === "blur(14px)" &&
    rimStyle.maskImage.includes("radial-gradient") &&
    glassStyle.backdropFilter === "none");
  // A full Today/adjacent-day round trip must change BOTH dates (and the Hijri
  // month narrative when required), yet preserve the photograph's original crop.
  const fullTodayHeight = photoCard.getBoundingClientRect().height;
  const minimumCanvasHeight = parseFloat(getComputedStyle(photoCard).minHeight);
  check("photograph canvas reaches the available viewport even if content is short",
    Number.isFinite(minimumCanvasHeight) && minimumCanvasHeight > 0 &&
    photoCard.getBoundingClientRect().height >= minimumCanvasHeight - 1);
  const originalPhotoHeight = getComputedStyle(photoCard, "::before").height;
  const originalPhotoPosition = getComputedStyle(photoCard, "::before").backgroundPosition;
  const originalPhotoUrl = photoCard.style.getPropertyValue("--mosque-background-image");
  for (const [offset, key] of [[1, "2026-10-22"], [-1, "2026-10-20"], [0, "2026-10-21"]]) {
    card.shadowRoot.querySelectorAll(".date-tab")[offset + 1].click();
    const current = card.shadowRoot.querySelector("ha-card");
    const h = card.shadowRoot.querySelector(".header");
    const description = h.querySelector(".month-description");
    const gregorian = h.querySelector(".gregorian");
    const hijri = h.querySelector(".hijri");
    check(`both selected-day calendars update for ${key}`,
      gregorian?.textContent === formatDate(key, ui) &&
      hijri?.textContent.startsWith(formatHijriDate(key, 0, ui)) &&
      description?.textContent === hijriMonthInfo(key, 0)?.summary_en);
    const candidateImage = getComputedStyle(current, "::before");
    const originalPixels = parseFloat(originalPhotoHeight);
    const candidatePixels = parseFloat(candidateImage.height);
    check(`image crop survives ${key}: original=${originalPhotoHeight}, next=${candidateImage.height}, photoFrame=${current.style.getPropertyValue("--mosque-photo-frame-height")}, stored=${JSON.stringify(card._backgroundFrame)}, url=${current.style.getPropertyValue("--mosque-background-image") === originalPhotoUrl}, position=${candidateImage.backgroundPosition} vs ${originalPhotoPosition}`,
      Number.isFinite(candidatePixels) && Math.abs(candidatePixels - originalPixels) < 2 &&
      current.style.getPropertyValue("--mosque-background-image") === originalPhotoUrl &&
      candidateImage.backgroundPosition === originalPhotoPosition);
    check(`adjacent day keeps full-viewport photograph while summary stays compact for ${key}`,
      current.getBoundingClientRect().height >= minimumCanvasHeight - 1 &&
      (offset === 0 || !current.querySelector(".prayer-panel")) &&
      current.querySelector(".timetable-shell").getBoundingClientRect().bottom <=
        current.getBoundingClientRect().bottom + 1);
  }
  // Date navigation re-creates its buttons; keyboard focus must follow the selected day.
  for (const index of [2, 0, 1]) {
    const button = card.shadowRoot.querySelectorAll(".date-tab")[index];
    button.focus();
    button.click();
    const replacement = card.shadowRoot.querySelectorAll(".date-tab")[index];
    check(`date navigation retains keyboard focus on tab ${index}`, card.shadowRoot.activeElement === replacement && replacement.getAttribute("aria-pressed") === "true");
  }
  card.shadowRoot.activeElement?.blur();
  // Reproduce a disappearing browser/dashboard scrollbar: a small width
  // change after Today is selected must NOT discard the original photo frame.
  const widthBeforeScrollbar = card.getBoundingClientRect().width;
  card.shadowRoot.querySelectorAll(".date-tab")[2].click();
  const initialFrame = card._backgroundFrame;
  const initiallyLockedWidth = card.shadowRoot.querySelector("ha-card").style.getPropertyValue("--mosque-photo-frame-width");
  const initiallyLockedHeight = card.shadowRoot.querySelector("ha-card").style.getPropertyValue("--mosque-photo-frame-height");
  card.style.width = `${Math.max(250, widthBeforeScrollbar - 12)}px`;
  card.shadowRoot.querySelectorAll(".date-tab")[0].click();
  const narrowed = card.shadowRoot.querySelector("ha-card");
  const narrowedImageStyle = getComputedStyle(narrowed, "::before");
  check("scrollbar-width changes do not reset background photo width or height",
    Boolean(initialFrame) &&
    narrowed.style.getPropertyValue("--mosque-photo-frame-width") === initiallyLockedWidth &&
    narrowed.style.getPropertyValue("--mosque-photo-frame-height") === initiallyLockedHeight &&
    Math.abs(parseFloat(narrowedImageStyle.width) - (initialFrame.width - 2)) < 2 &&
    Math.abs(parseFloat(narrowedImageStyle.height) - (initialFrame.height - 4)) < 2);
  card.style.width = "";
  card.shadowRoot.querySelectorAll(".date-tab")[1].click();
  render();
  const rules = card.shadowRoot.querySelector("style")?.sheet?.cssRules;
  check("bundled CSS module loads responsive rules", Boolean(rules?.length) && [...rules].some(rule => /max-width\s*:\s*28rem/.test(rule.conditionText || "")));
  const narrowRules = [...rules].find(rule => /max-width\s*:\s*28rem/.test(rule.conditionText || ""))?.cssRules;
  check("narrow table first-column rule parses correctly", [...(narrowRules || [])].some(rule => rule.selectorText === "th:first-child" && rule.style.width === "auto"));
  const panelStyle = getComputedStyle(card.shadowRoot.querySelector(".panel"));
  const gridStyle = getComputedStyle(card.shadowRoot.querySelector(".panels"));
  const sharedSummary = card.shadowRoot.querySelector(".summary-shell");
  const summaryStyle = getComputedStyle(sharedSummary);
  const timetableStyle = getComputedStyle(card.shadowRoot.querySelector(".timetable-shell"));
  const timetable = card.shadowRoot.querySelector(".timetable-shell");
  const glassHeader = getComputedStyle(timetable.querySelector("thead"));
  const glassFooter = getComputedStyle(timetable.querySelector(".date-tabs"));
  const isTransparent = style => style.backgroundColor === "rgba(0, 0, 0, 0)" &&
    style.backgroundImage === "none";
  check("summary and timetable retain the same stronger glass material",
    summaryStyle.backgroundImage === timetableStyle.backgroundImage &&
    summaryStyle.backdropFilter === timetableStyle.backdropFilter &&
    summaryStyle.backdropFilter.includes("blur(20px)") &&
    summaryStyle.borderRadius === timetableStyle.borderRadius &&
    summaryStyle.borderColor === timetableStyle.borderColor &&
    summaryStyle.boxShadow === timetableStyle.boxShadow &&
    summaryStyle.boxShadow !== "none" &&
    isTransparent(glassHeader) && isTransparent(glassFooter) &&
    getComputedStyle(sharedSummary, "::before").backgroundImage ===
      getComputedStyle(timetable, "::before").backgroundImage);
  check("glass foreground inherits readable Home Assistant text colours",
    summaryStyle.color === timetableStyle.color &&
    getComputedStyle(sharedSummary.querySelector(".hijri")).color !== "rgba(0, 0, 0, 0)" &&
    getComputedStyle(timetable.querySelector("tbody td")).color !== "rgba(0, 0, 0, 0)");
  check("outer background does not apply a configurable opacity overlay",
    !photoCard.style.getPropertyValue("--mosque-overlay") &&
    !Object.prototype.hasOwnProperty.call(card._config, "mosque_background_opacity"));
  const bothClocks = [...sharedSummary.querySelectorAll(".prayer-panel")];
  check("single frosted glass surface holds mosque identity and both countdowns",
    sharedSummary.querySelector(":scope > header") !== null &&
    sharedSummary.querySelector(":scope > .panels") !== null &&
    bothClocks.length === 2 &&
    summaryStyle.borderRadius === "18px" &&
    summaryStyle.backdropFilter.includes("blur(20px)") &&
    summaryStyle.marginBottom === "16px" &&
    panelStyle.display === "flex" && panelStyle.borderWidth === "0px" &&
    panelStyle.borderRadius === "0px" && gridStyle.display === "grid");
  const [salahStyle, jamaatStyle] = bothClocks.map(panel => getComputedStyle(panel));
  const [salahClockStyle, jamaatClockStyle] = bothClocks.map(panel => getComputedStyle(panel.querySelector(".count")));
  const [salahEventStyle, jamaatEventStyle] = bothClocks.map(panel => getComputedStyle(panel.querySelector(".event")));
  check("Salah and Jamaat use identical backgrounds, padding, countdown sizes and type hierarchy",
    salahStyle.backgroundColor === jamaatStyle.backgroundColor &&
    salahStyle.backgroundImage === jamaatStyle.backgroundImage &&
    salahStyle.padding === jamaatStyle.padding &&
    salahClockStyle.fontSize === jamaatClockStyle.fontSize &&
    salahClockStyle.color === jamaatClockStyle.color &&
    salahEventStyle.fontSize === jamaatEventStyle.fontSize);
  check("countdown divider changes direction only on narrow cards",
    width <= 336
      ? jamaatStyle.borderBlockStartWidth === "1px" && jamaatStyle.borderInlineStartWidth === "0px"
      : jamaatStyle.borderInlineStartWidth === "1px" && jamaatStyle.borderBlockStartWidth === "0px");
  const summaryRect = sharedSummary.getBoundingClientRect();
  check("both countdowns remain contained within the shared card",
    [...sharedSummary.querySelectorAll(".prayer-panel")].every(panel => {
      const rect = panel.getBoundingClientRect();
      return rect.left >= summaryRect.left - 1 && rect.right <= summaryRect.right + 1 &&
        rect.top >= summaryRect.top - 1 && rect.bottom <= summaryRect.bottom + 1;
    }));
  check("container layout uses one column on mobile and two on tablet", gridStyle.gridTemplateColumns.split(" ").length === (width <= 336 ? 1 : 2));
  check("card language and direction match configuration", card.getAttribute("lang") === language && card.getAttribute("dir") === ui.dir);
  check("summary icon silhouettes are hidden from accessibility", card.shadowRoot.querySelectorAll(".panel-silhouette[aria-hidden=\"true\"] svg").length === 2);
  check("day controls follow timetable, not countdowns", Boolean(card.shadowRoot.querySelector(".timetable-shell > .date-tabs")));
  check("Hijri month subtext follows header dates without duplicate month panel", Boolean(card.shadowRoot.querySelector("header > .month-description")) && !card.shadowRoot.querySelector(".hijri-month-info"));
  const heading = card.shadowRoot.querySelector(".header");
  const hijriBounds = heading.querySelector(".hijri").getBoundingClientRect();
  const gregorianBounds = heading.querySelector(".gregorian").getBoundingClientRect();
  const descriptionBounds = heading.querySelector(".month-description").getBoundingClientRect();
  check("month description occupies its own full header row at every viewport",
    getComputedStyle(heading).display === "grid" &&
    descriptionBounds.top >= Math.max(hijriBounds.bottom, gregorianBounds.bottom) - 1 &&
    descriptionBounds.width >= heading.getBoundingClientRect().width - 1);
  for (const mode of ["standard", "detailed"]) {
    render({show_month_view: true, detail_level: mode});
    const datedHeader = card.shadowRoot.querySelector(".header");
    const titleBounds = datedHeader.querySelector("h2").getBoundingClientRect();
    const dateBounds = datedHeader.querySelector(".gregorian").getBoundingClientRect();
    const action = datedHeader.querySelector(".month-toggle");
    const icon = action?.querySelector("ha-icon");
    const label = action?.querySelector("span");
    const actionBounds = action?.getBoundingClientRect();
    const headerBounds = datedHeader.getBoundingClientRect();
    const iconSize = icon?.getBoundingClientRect().height;
    const labelSize = label ? Number.parseFloat(getComputedStyle(label).fontSize) : 0;
    const alignment = {
      mode, width, dir: ui.dir,
      title: {top: titleBounds.top, left: titleBounds.left, right: titleBounds.right, height: titleBounds.height},
      action: actionBounds && {top: actionBounds.top, bottom: actionBounds.bottom, left: actionBounds.left, right: actionBounds.right},
      date: {top: dateBounds.top, left: dateBounds.left, right: dateBounds.right},
      header: {top: headerBounds.top, left: headerBounds.left, right: headerBounds.right},
      gridColumns: getComputedStyle(datedHeader).gridTemplateColumns,
    };
    check(`monthly action shares the mosque title row and sits above Gregorian in ${mode}: ${JSON.stringify(alignment)}`,
      Boolean(actionBounds && titleBounds && dateBounds && headerBounds) &&
      Math.abs(actionBounds.top - titleBounds.top) <= 3 &&
      actionBounds.bottom <= dateBounds.top + 1 &&
      (ui.dir === "rtl"
        ? Math.abs(actionBounds.left - headerBounds.left) <= 2
        : Math.abs(actionBounds.right - headerBounds.right) <= 2));
    check(`calendar icon and label use matching sizes and stay within the header in ${mode}`,
      Boolean(icon && label && iconSize && labelSize) &&
      Math.abs(iconSize - labelSize) <= 2 &&
      actionBounds.left >= headerBounds.left - 1 &&
      actionBounds.right <= headerBounds.right + 1 &&
      (width > 528
        ? getComputedStyle(label).display !== "none"
        : getComputedStyle(label).display === "none"));
  }
  render();
  check("mosque timezone used for absolute times", card.shadowRoot.querySelector('[data-panel="salah"] .absolute').textContent === `${digits(5)}:${digits(45)}`);
  check("local beginning countdown", card.shadowRoot.querySelector('[data-panel="salah"] .count').textContent === `${digits(0)}:${digits(5)}:${digits(0)}`);
  check("Ramadan has textual Taraweeh fallback", card.shadowRoot.textContent.includes("After Isha Jamaat"));
  check("published Fajr end remains visible", card.shadowRoot.querySelector(".fajr-end bdi")?.textContent === `${digits(7)}:${digits(30)}`);
  const labelLanguages = [...card.shadowRoot.querySelectorAll("tbody th .prayer-labels")].map(label => [...label.querySelectorAll("bdi")].map(value => value.getAttribute("lang")));
  const expectedLanguages = bilingual ? [language, language === "en" ? "ar" : "en"] : [language];
  check("prayer labels use the selected languages", labelLanguages.length === 5 && labelLanguages.every(languages => JSON.stringify(languages) === JSON.stringify(expectedLanguages)));
  const numericNodes = [...card.shadowRoot.querySelectorAll("tbody td, .count, .absolute, [data-ramadan] .event")];
  check("numeric times use LTR isolation", numericNodes.length > 0 && numericNodes.every(element => element.querySelector('bdi[dir="ltr"]')) && [...card.shadowRoot.querySelectorAll('bdi[dir="ltr"]')].every(element => getComputedStyle(element).direction === "ltr"));
  card._render(Date.parse(time(4, 50)));
  check("pending Fajr Jamaat replaces the previous congregation", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.next_jamaat"));
  check("upcoming Jamaat shows its countdown", card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent === `${digits(0)}:${digits(25)}:${digits(0)}`);
  card._render(Date.parse(time(5, 15)));
  check("exact Jamaat becomes previous event", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.previous_jamaat"));
  check("previous Jamaat displays published times", Boolean(card.shadowRoot.querySelector('[data-panel="jamaat"] .prayer-times bdi')));
  check("previous Jamaat shows live elapsed time", card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent.includes(tr(ui, "status.elapsed").split("{time}")[0]) && card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent.includes(":"));
  render({title: '<img src="x" onerror="window.injected=true">'});
  check("title uses literal text rather than executable markup", card.shadowRoot.querySelector("h2").textContent.startsWith("<img") && !card.shadowRoot.querySelector("img") && !window.injected);
  render({title: "مسجد الرحمة · Long mixed mosque title ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 · المسجد الكبير"});
  check("long mixed-direction title fits without overflow", fits(card) && card.shadowRoot.querySelector("h2").getAttribute("dir") === "auto");
  render();
  check("Gregorian and calculated Hijri dates are visible", card.shadowRoot.querySelector(".gregorian")?.textContent && card.shadowRoot.querySelector(".hijri")?.textContent.includes(tr(ui, "card.hijri_calculated")));
  check("Hijri date appears before the independent Gregorian date", card.shadowRoot.querySelector("header").children[1] === card.shadowRoot.querySelector(".hijri") && card.shadowRoot.querySelector("header").children[2] === card.shadowRoot.querySelector(".gregorian"));
  render({show_gregorian_date: false});
  check("Gregorian can be hidden while Hijri remains visible", !card.shadowRoot.querySelector(".gregorian") && Boolean(card.shadowRoot.querySelector(".hijri")));
  render({show_hijri_date: false});
  check("Hijri can be hidden while Gregorian remains visible", !card.shadowRoot.querySelector(".hijri") && Boolean(card.shadowRoot.querySelector(".gregorian")) && !card.shadowRoot.querySelector(".month-description"));
  render();
  card.hass = {...hass, states: {...hass.states, [config.entity]: {state: data.date, attributes: {...data, show_hijri_date: false}}}};
  check("mosque-configured Hijri visibility remains authoritative", !card.shadowRoot.querySelector(".hijri") && Boolean(card.shadowRoot.querySelector(".gregorian")) && !card.shadowRoot.querySelector(".month-description"));
  card.hass = {...hass, states: {...hass.states, [config.entity]: {state: "2026-10-23", attributes: {...data, date: "2026-10-23", second_khutbah: "2026-10-23T12:20:00Z"}}}};
  check("Friday published second Khutbah remains isolated", Boolean(card.shadowRoot.querySelector('.khutbah bdi[dir="ltr"]')));
  card.hass = hass; card._render(Date.parse(time(4, 40)));
  check("upcoming row has accessible emphasis", card.shadowRoot.querySelector("tbody tr").getAttribute("aria-current") === "true");
  render({}, time(8));
  check("previous Jamaat follows completed Fajr", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.previous_jamaat"));
  check("Next Salah countdown and Previous Jamaat elapsed clock are both visible", card.shadowRoot.querySelectorAll(".prayer-panel .count").length === 2 && Boolean(card.shadowRoot.querySelector('[data-panel="jamaat"] .count')));
  render({detail_level: "standard", time_format: "12h", show_salah_countdown: false});
  check("single visible panel fills width", card.shadowRoot.querySelectorAll(".prayer-panel").length === 1 && Boolean(card.shadowRoot.querySelector("header .month-description")));
  check("12-hour absolute times", /(?:am|pm|ص|م)\s*$/i.test(card.shadowRoot.querySelector("tbody td > bdi").textContent));
  render({}, time(4, 41));
  const scrollRegion = card.shadowRoot.querySelector(".table-scroll"); scrollRegion.focus();
  const stableTable = card.shadowRoot.querySelector("table");
  const prayerCell = stableTable.querySelector("tbody th");
  const range = document.createRange(); range.selectNodeContents(prayerCell);
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  const selectedText = selection.toString();
  card._tick(Date.parse(time(4, 41)) + 1000);
  check("ordinary ticks retain table nodes and text selection", card.shadowRoot.querySelector("table") === stableTable && selection.toString() === selectedText);
  selection.removeAllRanges();
  check("countdown tick preserves table keyboard focus", card.shadowRoot.activeElement === card.shadowRoot.querySelector(".table-scroll"));
  check("card fits its viewport", fits(card));
  document.documentElement.style.fontSize = "200%";
  const fitsScaledText = card.getBoundingClientRect().width <= width + 1 && document.documentElement.scrollWidth <= width + 1 && card.shadowRoot.querySelector(".content").scrollWidth <= card.shadowRoot.querySelector(".content").clientWidth + 1 && card.shadowRoot.querySelector(".content").clientWidth > 0 && [...card.shadowRoot.querySelectorAll(".panel, h2")].every(element => element.getBoundingClientRect().width <= card.shadowRoot.querySelector(".content").clientWidth + 1);
  const scaledRegion = card.shadowRoot.querySelector(".table-scroll");
  const overflowing = scaledRegion.scrollWidth > scaledRegion.clientWidth + 1;
  check("overflow has visible scrolling guidance", !overflowing || getComputedStyle(card.shadowRoot.querySelector(".scroll-help")).display !== "none");
  scaledRegion.scrollLeft = ui.dir === "rtl" ? -50 : 50;
  check("overflow region can scroll without widening the card", !overflowing || Math.abs(scaledRegion.scrollLeft) > 0);
  check("RTL overflow uses Chromium negative scrollLeft", ui.dir !== "rtl" || !overflowing || scaledRegion.scrollLeft < 0);
  const savedScroll = scaledRegion.scrollLeft;
  card._tick(Date.parse(time(4, 41)) + 2000);
  check("countdown tick preserves horizontal scroll position", scaledRegion.scrollLeft === savedScroll);
  document.documentElement.style.fontSize = "";
  check("card contains 200% text without overflowing", fitsScaledText);
  const columns = getComputedStyle(card.shadowRoot.querySelector(".ramadan-grid")).gridTemplateColumns.split(" ").length;
  check("responsive Ramadan grid", columns === (width <= 420 ? 2 : 3));
  document.documentElement.style.setProperty("--primary-text-color", "rgb(250, 250, 250)");
  check("dark theme follows HA variables", getComputedStyle(card).color === "rgb(250, 250, 250)");
  document.documentElement.style.setProperty("--primary-text-color", "rgb(20, 20, 20)");
  check("light theme follows HA variables", getComputedStyle(card).color === "rgb(20, 20, 20)");

  const yamlTitle = "My Mosque";
  const editor = new SalahTimetableCardEditor(); editor.setConfig({...config, title: yamlTitle}); editor.hass = hass; document.body.append(editor);
  const editorForm = editor.shadowRoot.querySelector(".form");
  check("graphical editor stylesheet applies grid and HA theme colors", getComputedStyle(editorForm).display === "grid" && getComputedStyle(editorForm).color === "rgb(20, 20, 20)");
  check("graphical editor omits the title field", !editor.shadowRoot.querySelector('input[type="text"], ha-textfield'));
  let lastConfig;
  editor.addEventListener("config-changed", event => { lastConfig = event.detail.config; editor.setConfig(event.detail.config); card.setConfig(event.detail.config); card._render(Date.parse(time(4, 40))); });
  const detail = editor.shadowRoot.querySelector('[data-option="detail_level"]');
  detail.focus(); detail.value = "standard"; detail.dispatchEvent(new Event("change", {bubbles: true}));
  check("graphical edits preserve and render the YAML title", lastConfig?.title === yamlTitle && card.shadowRoot.querySelector("h2")?.textContent === yamlTitle);
  check("configuration echo preserves focused detail selector", editor.shadowRoot.activeElement === detail);
  check("editor removes duplicate timetable sensor selector",
    !editor.shadowRoot.querySelector("ha-selector"));
  const secondEntity = "sensor.second_prayer_timetable";
  const multiEditor = new SalahTimetableCardEditor();
  multiEditor.setConfig({entity: "sensor.example_prayer_timetable", language,
    mosque_entities: ["sensor.example_prayer_timetable", secondEntity]});
  multiEditor.hass = {...hass, states: {...hass.states, [secondEntity]: {
    state: data.date, attributes: {...data, mosque_name: "Second Mosque"},
  }}};
  document.body.append(multiEditor);
  multiEditor.addEventListener("config-changed", event => multiEditor.setConfig(event.detail.config));
  const mosqueRows = () => [...multiEditor.shadowRoot.querySelectorAll(".mosque-choice")];
  check("ordered mosque editor shows six-dot grips and first-mosque indicator",
    mosqueRows().length === 2 &&
    mosqueRows()[0].querySelector(".mosque-grip ha-icon")?.getAttribute("icon") === "mdi:drag-vertical" &&
    mosqueRows()[0].textContent.includes(tr(ui, "editor.mosque_first")) &&
    !mosqueRows()[0].hasAttribute("draggable"));
  mosqueRows()[1].querySelector(".mosque-move-up").click();
  check("keyboard-friendly reorder updates primary mosque",
    multiEditor._config.entity === secondEntity &&
    multiEditor._config.mosque_entities[0] === secondEntity);
  const firstBox = multiEditor.shadowRoot.querySelector(".mosque-choice input");
  firstBox.checked = false;
  firstBox.dispatchEvent(new Event("change", {bubbles: true}));
  check("unselected mosque cannot be dragged or moved",
    multiEditor.shadowRoot.querySelectorAll(".mosque-choice").length === 2 &&
    [...multiEditor.shadowRoot.querySelectorAll(".mosque-choice")].some(row =>
      row.getAttribute("data-selected") === "false" &&
      row.querySelector(".mosque-grip")?.disabled &&
      row.querySelector(".mosque-move-up")?.disabled));
  editor.hass = {...hass, states: {...hass.states}};
  check("hass state updates preserve focused detail selector", editor.shadowRoot.activeElement === detail);
  check("obsolete Jamaat mode editor removed", !editor.shadowRoot.textContent.includes("Jamaat panel"));
  const update = (key, value) => {
    const control = editor.shadowRoot.querySelector(`[data-option="${key}"]`);
    if (typeof value === "boolean") control.checked = value; else control.value = String(value);
    control.dispatchEvent(new Event("change", {bubbles: true}));
    check(`editor ${key}=${value} updates configuration`, lastConfig[key] === value);
  };
  for (const value of ["ar", "en", "auto", language]) {
    update("language", value);
    const expected = value === "ar" ? "rtl" : "ltr";
    check(`editor language=${value} updates direction`, editor.getAttribute("dir") === expected && card.getAttribute("dir") === expected);
    check(`editor language=${value} preserves focused detail selector`, editor.shadowRoot.activeElement === detail);
  }
  for (const value of [false, true, bilingual]) update("bilingual_prayer_labels", value);
  check("graphical language and bilingual controls round trip", lastConfig.language === language && lastConfig.bilingual_prayer_labels === bilingual);
  for (const [key, values] of Object.entries({detail_level: ["compact", "standard", "detailed"], time_format: ["12h", "24h"], hijri_adjustment: [-3, 3, 0]})) for (const value of values) update(key, value);
  const visibilityOptions = Object.keys(visibility(card));
  for (const key of visibilityOptions) for (const value of [false, true]) {
    update(key, value);
    const expected = Object.fromEntries(visibilityOptions.map(option => [option, true]));
    expected[key] = value;
    if (key === "show_ramadan_details") expected.show_sehri_countdown = expected.show_iftar_countdown = value;
    check(`editor ${key}=${value} changes the expected visible content`, Object.entries(visibility(card)).every(([option, visible]) => visible === expected[option]));
  }
  const restored = new SalahTimetableCardEditor(); restored.setConfig(JSON.parse(JSON.stringify(lastConfig))); restored.hass = hass;
  check("restored graphical configuration", restored._config.title === yamlTitle && restored.shadowRoot.querySelector('[data-option="detail_level"]').value === lastConfig.detail_level);
  check("all graphical options survive configuration reload", [...restored.shadowRoot.querySelectorAll("[data-option]")].every(control => {
    const key = control.getAttribute("data-option");
    if (control.localName === "ha-switch") return control.checked === lastConfig[key];
    if (key === "mosque_background") {
      return control.value === (lastConfig.show_mosque_background ? lastConfig.mosque_background : "none");
    }
    return control.value === String(lastConfig[key]);
  }));
  const reminderFields = [
    {value: "fajr_begin", label: "Fajr beginning"},
    {value: "fajr_jamaat", label: "Fajr Jamaat"},
    {value: "jumuah", label: "Jumu’ah Jamaat"},
  ];
  const reminderOptions = {
    mosques: ["First", "Second"].map(name => ({
      id: name.toLowerCase(), name: `${name} masjid`,
      time_zone: "Europe/London", fields: reminderFields, ready: true,
    })),
    notification_actions: [
      {value: "notify.mobile_app_phone", label: "Phone Companion app", integration: "mobile_app", integration_name: "Companion app", device_type: "phone", device_type_name: "Phone"},
      {value: "notify.browser", label: "Browser", integration: "html5", integration_name: "HTML5", device_type: "computer", device_type_name: "Computer"},
    ],
    notification_entities: [{value: "notify.tablet", label: "Tablet", integration: "mobile_app", integration_name: "Companion app", device_type: "tablet", device_type_name: "Tablet"}],
    media_players: [
      {value: "media_player.hall", label: "Hall speaker", integration: "music_assistant", integration_name: "Music Assistant", device_type: "speaker", device_type_name: "Speaker"},
      {value: "media_player.kitchen", label: "Kitchen speaker", integration: "music_assistant", integration_name: "Music Assistant", device_type: "speaker", device_type_name: "Speaker"},
      {value: "media_player.hall_cast", label: "Hall speaker", integration: "cast", integration_name: "Google Cast", device_type: "speaker", device_type_name: "Speaker"},
      {value: "media_player.tv", label: "Living room TV", integration: "cast", integration_name: "Google Cast", device_type: "tv", device_type_name: "TV"},
    ],
  };
  const reminderWrites = [], reminderPreviews = [];
  let finishSave;
  const reminderHass = {
    states: {"media_player.hall": {attributes: {friendly_name: "Hall speaker"}}, "media_player.kitchen": {attributes: {friendly_name: "Kitchen speaker"}}},
    async callWS(payload) {
      if (payload.type === "salah_timetable/reminder_options") return reminderOptions;
      reminderPreviews.push(payload);
      return {config: {alias: payload.name}};
    },
    callApi(...args) {
      reminderWrites.push(args);
      return new Promise(resolve => { finishSave = resolve; });
    },
  };
  editor.hass = {...reminderHass, user: {is_admin: true}};
  const launch = editor.shadowRoot.querySelector(".reminder-setup");
  check("reminder setup is in the editor", launch && !launch.hidden && !card.shadowRoot.querySelector(".reminder-setup"));
  launch.focus();
  launch.click();
  await new Promise(resolve => setTimeout(resolve, 0));
  const wizard = document.querySelector("salah-reminder-wizard");
  check("editor launches reminder wizard", !!wizard);
  await wizard.ready;
  const wr = wizard.shadowRoot;
  const wi = key => [...wr.querySelectorAll("input")].find(node => node.dataset.key === key);
  const wb = text => [...wr.querySelectorAll("button")].find(node => node.textContent === text);
  const wc = text => wb(text).click();
  const wt = (key, value) => {
    wi(key).value = value;
    wi(key).dispatchEvent(new Event("input"));
  };
  const wf = (key, value) => {
    const select = wr.querySelector(`[data-key="filter:${key}"]`);
    select.value = value; select.dispatchEvent(new Event("change"));
  };
  const wizardFits = () => {
    const dialog = wr.querySelector("dialog"), main = wr.querySelector("main");
    return dialog.getBoundingClientRect().width <= width &&
      dialog.scrollWidth <= dialog.clientWidth + 1 &&
      main.scrollWidth <= main.clientWidth + 1;
  };
  check("reminder opens native modal", wr.querySelector("dialog").matches(":modal"));
  wi("mosque:first").click(); wi("mosque:second").click(); wc("Next");
  check("reminder step receives keyboard focus", wr.activeElement === wr.querySelector("main"));
  wi("field:fajr_begin").click(); wi("field:fajr_jamaat").click(); wc("Next");
  wi("field:fajr_begin").click(); wi("field:jumuah").click(); wc("Next");
  wt("begin_minutes", "5"); wt("jamaat_minutes", "15"); wc("Next");
  check("reminder hides unused beginning offset", !wi("begin_minutes"));
  wt("jamaat_minutes", "20"); wc("Back");
  check("reminder Back retains input", wi("begin_minutes").value === "5");
  wc("Next"); wc("Next");
  check("beginning delivery opens Notifications tab", wizard._activeDeliveryKind() === "beginning" && wb("Notifications").getAttribute("aria-selected") === "true" && !wi("media_player:media_player.hall"));
  check("notification selection shows exact action and entity IDs", wr.textContent.includes("notify.mobile_app_phone") && wr.textContent.includes("notify.tablet"));
  wf("integration", "mobile_app");
  check("Companion app filter includes both notification routes", !!wi("notification_actions:notify.mobile_app_phone") && !!wi("notification_entities:notify.tablet") && !wi("notification_actions:notify.browser"));
  wf("device_type", "phone");
  check("notification provider and type filters combine", !!wi("notification_actions:notify.mobile_app_phone") && !wi("notification_entities:notify.tablet"));
  wi("notification_actions:notify.mobile_app_phone").click();
  // Exercise actual keyboard navigation and roving focus on the tab controls.
  wb("Notifications").dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowRight", bubbles: true}));
  check("Sound tab keyboard selection retains focus", wb("Sound").getAttribute("aria-selected") === "true" && wr.activeElement === wb("Sound"));
  check("speaker selection shows friendly name and entity ID", wr.textContent.includes("Hall speaker (media_player.hall)"));
  wf("integration", "music_assistant"); wf("device_type", "speaker");
  check("Music Assistant filter separates duplicate speaker names", !!wi("media_player:media_player.hall") && !wi("media_player:media_player.hall_cast") && !wi("media_player:media_player.tv"));
  wi("media_player:media_player.hall").click();
  wt("name", "LongReminderName".repeat(6));
  const beginningRecording = "media-source://media_source/local/" + "recording".repeat(40) + ".mp3";
  wt("media_content_id", beginningRecording);
  check("reminder delivery fits mobile", wizardFits());
  wf("integration", "cast"); wf("device_type", "tv");
  check("filters retain hidden speaker and media settings", !wi("media_player:media_player.hall") && !!wi("media_player:media_player.tv") && wi("media_content_id").value === beginningRecording && wr.textContent.includes("1 selected destination hidden"));
  wf("integration", "music_assistant");
  check("combined filters report no matches without clearing selections", wr.textContent.includes("No destinations match these filters") && wi("media_content_id").value === beginningRecording);
  wf("device_type", "speaker");
  check("returning to Music Assistant retains selected player", wi("media_player:media_player.hall").checked);
  wc("Notifications");
  check("notification selection survives Sound tab", wi("notification_actions:notify.mobile_app_phone").checked);
  wc("Next");
  check("Jamaat delivery is separate", wizard._activeDeliveryKind() === "jamaat" && !wi("notification_actions:notify.mobile_app_phone").checked);
  check("Jamaat starts with independent filters", wr.querySelector('[data-key="filter:integration"]').value === "" && wr.querySelector('[data-key="filter:device_type"]').value === "");
  wf("integration", "mobile_app"); wf("device_type", "tablet");
  wi("notification_entities:notify.tablet").click(); wc("Sound");
  check("Jamaat sound does not inherit beginning speakers", !wi("media_player:media_player.hall").checked);
  wi("media_player:media_player.kitchen").click();
  wt("media_content_id", "library://track/456"); wt("media_content_type", "music");
  wc("Back");
  check("Back restores beginning delivery", wizard._activeDeliveryKind() === "beginning" && wi("notification_actions:notify.mobile_app_phone").checked);
  check("Back retains category-specific filters", wr.querySelector('[data-key="filter:integration"]').value === "mobile_app" && wr.querySelector('[data-key="filter:device_type"]').value === "phone");
  wc("Sound");
  check("beginning sound survives independent Jamaat setup", wi("media_player:media_player.hall").checked && wi("media_content_id").value === beginningRecording);
  wc("Next");
  check("Jamaat settings survive Back", wizard._activeDeliveryKind() === "jamaat" && wi("media_player:media_player.kitchen").checked && wi("media_content_id").value === "library://track/456");
  wc("Next");
  check("reminder review fits mobile", wizardFits());
  check("reminder review contains full configuration",
    wr.textContent.includes("5 minutes before") &&
    wr.textContent.includes("20 minutes before") &&
    wr.textContent.includes("all published congregations") &&
    wr.textContent.includes("Beginning reminders delivery") &&
    wr.textContent.includes("Jamaat reminders delivery") &&
    wr.textContent.includes("Hall speaker (media_player.hall)") &&
    wr.textContent.includes("Kitchen speaker (media_player.kitchen)"));
  check("reminder no write before Finish", reminderWrites.length === 0);
  wc("Finish"); await Promise.resolve(); await Promise.resolve();
  check("reminder saves one normal automation",
    reminderWrites.length === 1 && reminderWrites[0][0] === "POST" &&
    reminderWrites[0][1].startsWith("config/automation/config/salah_reminders_"));
  check("saved delivery preserves category routing", reminderPreviews[0].delivery.beginning.notification_actions[0] === "notify.mobile_app_phone" && reminderPreviews[0].delivery.beginning.media_players[0] === "media_player.hall" && reminderPreviews[0].delivery.jamaat.notification_entities[0] === "notify.tablet" && reminderPreviews[0].delivery.jamaat.media_content_id === "library://track/456");
  check("reminder save locks buttons", [...wr.querySelectorAll("button")].every(node => node.disabled));
  wizard._next();
  check("reminder duplicate Finish blocked", reminderWrites.length === 1);
  finishSave({result: "ok"}); await Promise.resolve(); await Promise.resolve();
  check("reminder saved automation link",
    wr.querySelector("a")?.getAttribute("href").startsWith("/config/automation/edit/salah_reminders_"));
  wc("Close");
  check("reminder Close restores launch focus", editor.shadowRoot.activeElement === launch);
  check("countdowns never write HA service or state", serviceCalls === 0);
  check("real browser resource registration", customElements.get("salah-timetable-card") === SalahTimetableCard && window.customCards.some(item => item.type === "salah-timetable-card"));
  card.remove(); check("disconnected card clears local timer", card._timer === null);
  // Keep a static native-DOM preview for optional CDP screenshots.
  document.body.prepend(card); card.disconnectedCallback(); card._render(Date.parse(time(4, 40))); card.shadowRoot.querySelector(".table-scroll").scrollLeft = 0;
  window.mountActionCard = detail_level => {
    const actionCard = new SalahTimetableCard();
    actionCard.setConfig({...config, detail_level, show_month_view: true, show_mosque_background: true, mosque_background: "masjid-al-haram"});
    const requests = [];
    actionCard.hass = {...hass, callWS(message) {
      requests.push(message);
      return Promise.resolve({rows: [{date: data.date, published: true, times: {fajr_begin: ["05:45"]}}]});
    }};
    document.body.prepend(actionCard);
    return {actionCard, requests};
  };
  parent.postMessage({kind: "salah-browser-result", status: "passed", width, language, bilingual, checks}, location.origin);
} catch (error) {
  parent.postMessage({kind: "salah-browser-result", status: "failed", width, language, bilingual, checks, error: error.stack || String(error)}, location.origin);
}

