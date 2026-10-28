/** Only add photographs after verifying redistribution rights and attribution. */
export const MOSQUE_BACKGROUNDS = Object.freeze([]);

/** Stable day-based rotation; independent of browser refreshes. */
export function chooseMosqueBackground(items, selection = "daily", day = "") {
  if (!Array.isArray(items) || !items.length || selection === "none") return null;
  if (selection !== "daily") return items.find(item => item.id === selection) || null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const epoch = Date.parse(day + "T00:00:00Z");
  if (!Number.isFinite(epoch)) return null;
  return items[((Math.floor(epoch / 86400000) % items.length) + items.length) % items.length];
}
