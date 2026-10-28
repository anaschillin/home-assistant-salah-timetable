import test from "node:test";
import assert from "node:assert/strict";
import {existsSync, readFileSync, statSync} from "node:fs";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
import {dirname, join} from "node:path";
import {MOSQUE_BACKGROUNDS, chooseMosqueBackground} from "../../custom_components/salah_timetable/frontend/mosque-backgrounds.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "../../custom_components/salah_timetable/frontend");

test("20 bundled mosque photos have local, verified metadata and stay under 250 KB", () => {
  assert.equal(MOSQUE_BACKGROUNDS.length, 20);
  assert.equal(new Set(MOSQUE_BACKGROUNDS.map(item => item.id)).size, 20);
  for (const item of MOSQUE_BACKGROUNDS) {
    assert.match(item.id, /^[a-z0-9-]+$/);
    assert.ok(item.name && item.country && item.photographer);
    assert.match(item.source_photo_id, /^photo-\d+-[a-f0-9]+$/);
    assert.equal(item.license_url, "https://unsplash.com/license");
    assert.match(item.source_url, /^https:\/\/unsplash\.com\/photos\//);
    assert.equal(item.path, `/salah_timetable/backgrounds/${item.id}.webp`);
    const path = join(root, "backgrounds", `${item.id}.webp`);
    assert.ok(existsSync(path), path);
    const bytes = readFileSync(path);
    assert.ok(bytes.subarray(0, 4).equals(Buffer.from("RIFF")), "WebP RIFF container");
    assert.equal(bytes.toString("ascii", 8, 12), "WEBP");
    assert.ok(statSync(path).size <= 250_000, path);
  }
});

test("bundled mosque photos match the provenance manifest and SHA-256", () => {
  const manifest = JSON.parse(readFileSync(join(root, "../../../docs/asset-provenance.json"), "utf8"));
  const entries = new Map(manifest.assets.map(asset => [asset.path, asset]));
  for (const item of MOSQUE_BACKGROUNDS) {
    const name = `custom_components/salah_timetable/frontend/backgrounds/${item.id}.webp`;
    const record = entries.get(name);
    assert.ok(record, `Missing provenance entry: ${name}`);
    assert.equal(record.rights, "permission_documented");
    assert.equal(record.owner, item.photographer);
    assert.equal(record.evidence, item.source_url);
    const bytes = readFileSync(join(root, "backgrounds", `${item.id}.webp`));
    const digest = createHash("sha256").update(bytes).digest("hex");
    assert.equal(record.sha256, digest);
  }
});

test("fixed selection, none and bad dates never show arbitrary images", () => {
  const [first] = MOSQUE_BACKGROUNDS;
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, first.id), first);
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, "nonexistent"), null);
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, "none"), null);
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, "daily", "bad-date"), null);
});

test("daily rotation is deterministic with no repeats until the set cycles", () => {
  const dates = Array.from({length: MOSQUE_BACKGROUNDS.length}, (_, i) =>
    new Date(Date.UTC(2026, 9, 28 + i)).toISOString().slice(0, 10));
  const ids = dates.map(day => chooseMosqueBackground(MOSQUE_BACKGROUNDS, "daily", day).id);
  assert.equal(new Set(ids).size, MOSQUE_BACKGROUNDS.length);
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, "daily", dates[0]).id, ids[0]);
  const cycle = new Date(Date.UTC(2026, 9, 28 + MOSQUE_BACKGROUNDS.length)).toISOString().slice(0, 10);
  assert.equal(chooseMosqueBackground(MOSQUE_BACKGROUNDS, "daily", cycle).id, ids[0]);
});
