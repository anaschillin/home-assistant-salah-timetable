/** Monthly timetable browsing, CSV export and source details.
 * These instance methods preserve request cancellation and selected-mosque guards.
 */
import {tr} from "./card-i18n.js?v=3.6.1";
import {node} from "./card-shared.js?v=3.6.1";

export const CardMonthlyMixin = Base => class extends Base {
  _loadMonth(year, month) {
    const day = new Date(Date.UTC(year, month - 1, 1));
    if (!Number.isFinite(day.valueOf()) || day.getUTCFullYear() < 1 || day.getUTCFullYear() > 9999) return;
    const entity = this._activeEntity();
    const token = ++this._monthRequest;
    const actualYear = day.getUTCFullYear(), actualMonth = day.getUTCMonth() + 1;
    this._monthView = true;
    this._monthState = {entity, year: actualYear, month: actualMonth, loading: true, rows: []};
    this._sourceState = null;
    this._render();
    if (typeof this._hass?.callWS !== "function") {
      this._monthState.loading = false;
      this._monthState.error = true;
      this._render();
      return;
    }
    this._hass.callWS({type: "salah_timetable/month", entity_id: entity, year: actualYear, month: actualMonth})
      .then(result => {
        if (token !== this._monthRequest || entity !== this._activeEntity()) return;
        this._monthState = {...this._monthState, loading: false, rows: result.rows || []};
        this._render();
      })
      .catch(() => {
        if (token !== this._monthRequest) return;
        this._monthState = {...this._monthState, loading: false, error: true};
        this._render();
      });
  }

  _exportYear() {
    const year = this._monthState?.year, entity = this._activeEntity();
    if (typeof this._hass?.callWS !== "function" || !year) return;
    this._hass.callWS({type: "salah_timetable/year_csv", entity_id: entity, year})
      .then(result => {
        if (entity !== this._activeEntity() || typeof result.csv !== "string") return;
        const blob = new Blob([result.csv], {type: "text/csv;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `salah-timetable-${year}.csv`;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      })
      .catch(() => { this._monthExportError = true; this._render(); });
  }

  _loadSources() {
    const entity = this._activeEntity();
    if (typeof this._hass?.callWS !== "function") return;
    this._sourceState = {loading: true};
    this._render();
    this._hass.callWS({type: "salah_timetable/sources", entity_id: entity})
      .then(result => {
        if (entity !== this._activeEntity() || !this._monthView) return;
        this._sourceState = {sources: Array.isArray(result.sources) ? result.sources : []};
        this._render();
      })
      .catch(() => { if (this._monthView) { this._sourceState = {error: true}; this._render(); } });
  }

  _cardActions(ui, displayDate) {
    if (!this._config.show_month_view) return null;
    const mode = this._config.detail_level;
    const actions = [];
    const action = (key, className, iconName, onClick) => {
      const label = tr(ui, key);
      const button = node("button", undefined, className);
      button.type = "button";
      button.title = label;
      button.setAttribute("aria-label", label);
      const icon = node("ha-icon");
      icon.setAttribute("icon", iconName);
      icon.setAttribute("aria-hidden", "true");
      button.append(icon);
      // Compact uses a disclosure menu, where action labels must remain visible.
      // Narrow-card icon-only styling applies only to the Standard/Detailed toolbar.
      button.append(node("span", label));
      button.addEventListener("click", event => {
        event.stopPropagation();
        onClick();
      });
      actions.push(button);
      return button;
    };
    const toggle = action(
      this._monthView ? "month.daily" : "month.title",
      "month-toggle",
      this._monthView ? "mdi:calendar-today" : "mdi:calendar-month",
      () => {
        if (this._monthView) {
          this._monthView = false;
          this._monthRequest++;
          this._render();
        } else {
          this._loadMonth(Number(displayDate.slice(0, 4)), Number(displayDate.slice(5, 7)));
        }
      },
    );
    toggle.setAttribute("aria-expanded", String(this._monthView));
    if (this._monthView) {
      action("month.csv_export", "month-action", "mdi:file-delimited-outline", () => this._exportYear());
      action("month.sources", "month-action", "mdi:information-outline", () => this._loadSources());
      action("month.refresh", "month-action", "mdi:refresh", () => this._loadMonth(this._monthState.year, this._monthState.month));
    }
    if (mode === "compact") {
      const menu = node("details", undefined, "card-actions-menu");
      const trigger = node("summary", undefined, "card-more-toggle");
      trigger.title = tr(ui, "card.more_actions");
      trigger.setAttribute("aria-label", trigger.title);
      trigger.addEventListener("click", event => event.stopPropagation());
      const icon = node("ha-icon");
      icon.setAttribute("icon", "mdi:dots-vertical");
      icon.setAttribute("aria-hidden", "true");
      trigger.append(icon, node("span", tr(ui, "card.more_actions")));
      const list = node("div", undefined, "card-menu-items");
      list.append(...actions);
      menu.append(trigger, list);
      return menu;
    }
    const toolbar = node("nav", undefined, "card-action-strip");
    toolbar.setAttribute("aria-label", tr(ui, "card.timetable_actions"));
    toolbar.append(...actions);
    return toolbar;
  }

  _monthlyPanel(ui) {
    const current = this._monthState;
    const panel = node("section", undefined, "monthly-shell");
    panel.setAttribute("aria-label", tr(ui, "month.title"));
    const toolbar = node("div", undefined, "month-toolbar");
    const prev = node("button", tr(ui, "month.previous"), "month-nav");
    prev.type = "button";
    prev.addEventListener("click", () => this._loadMonth(current.year, current.month - 1));
    const label = node("h3", new Intl.DateTimeFormat(ui.locale || "en-GB", {month: "long", year: "numeric", timeZone: "UTC"}).format(new Date(Date.UTC(current.year, current.month - 1, 15))));
    const next = node("button", tr(ui, "month.next"), "month-nav");
    next.type = "button";
    next.addEventListener("click", () => this._loadMonth(current.year, current.month + 1));
    toolbar.append(prev, label, next);
    panel.append(toolbar);
    if (current.loading) panel.append(node("p", tr(ui, "month.loading"), "note"));
    else if (current.error) panel.append(node("p", tr(ui, "month.error"), "note"));
    else {
      const scroll = node("div", undefined, "table-scroll");
      scroll.setAttribute("tabindex", "0");
      const table = node("table", undefined, "monthly-table");
      const caption = node("caption", tr(ui, "month.caption"), "sr-only");
      const head = node("thead"), headings = node("tr");
      for (const key of ["month.date", "prayer.fajr", "prayer.dhuhr", "prayer.asr", "prayer.maghrib", "prayer.isha", "prayer.jumuah"]) {
        const th = node("th", tr(ui, key)); th.scope = "col"; headings.append(th);
      }
      head.append(headings);
      const body = node("tbody");
      const prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha", "jumuah"];
      for (const item of current.rows) {
        const row = node("tr");
        const dateCell = node("th", item.date.slice(-2));
        dateCell.scope = "row";
        row.append(dateCell);
        for (const prayer of prayers) {
          const cell = node("td");
          const fields = prayer === "jumuah" ? ["jumuah"] : [`${prayer}_begin`, `${prayer}_jamaat`];
          const values = fields.flatMap(field => Array.isArray(item.times?.[field]) ? item.times[field] : []);
          cell.textContent = values.length ? values.join(" · ") : "—";
          row.append(cell);
        }
        if (!item.published) row.className = "missing-date";
        body.append(row);
      }
      table.append(caption, head, body);
      scroll.append(table);
      panel.append(scroll);
    }
    if (this._monthExportError) panel.append(node("p", tr(ui, "month.export_error"), "note"));
    if (this._sourceState) {
      const list = node("div", undefined, "source-summary");
      if (this._sourceState.loading) list.append(node("p", tr(ui, "month.loading")));
      else if (this._sourceState.error) list.append(node("p", tr(ui, "month.error")));
      else {
        list.append(node("h4", tr(ui, "month.sources")));
        for (const source of this._sourceState.sources) {
          list.append(node("p", `${source.source_id}: ${source.first_date} – ${source.last_date} · ${source.rows} rows · ${source.format || "legacy"} · ${source.check_status}`));
        }
      }
      panel.append(list);
    }
    return panel;
  }
};
