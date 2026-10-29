/** CI fixture regression: real HA can advance a day during the browser test. */
import assert from "node:assert/strict";
import {test} from "node:test";
import {smokeDateWindow} from "../../scripts/live_dates.mjs";

test("smoke fixture includes the following UTC day", () => {
  assert.deepEqual(smokeDateWindow(new Date("2026-10-28T23:58:30Z")), {
    today: "2026-10-28", next: "2026-10-29",
    days: ["2026-10-28", "2026-10-29"], nextYearDays: [],
  });
});

test("December 31 builds two annual sources without mixing their years", () => {
  assert.deepEqual(smokeDateWindow(new Date("2026-12-31T23:59:59Z")), {
    today: "2026-12-31", next: "2027-01-01",
    days: ["2026-12-31"], nextYearDays: ["2027-01-01"],
  });
});

test("leap-year date window contains February 29", () => {
  assert.deepEqual(smokeDateWindow(new Date("2028-02-28T23:59:00Z")).days, ["2028-02-28", "2028-02-29"]);
});
