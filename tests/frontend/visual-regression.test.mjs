import test from "node:test";
import assert from "node:assert/strict";
import {deflateSync} from "node:zlib";
import {decodePng, pixelDifference, visualDiffDecision} from "../../scripts/compare_screenshots.mjs";

// The decoder intentionally ignores checksums: screenshots come only from the
// locally launched Chromium, not user-supplied images.
function png(width, height, pixels, filter = 0) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0); header.writeUInt32BE(height, 4);
  header[8] = 8; header[9] = 6;
  const rows = [];
  for (let y = 0; y < height; y++) rows.push(Buffer.from([filter]), pixels.subarray(y * width * 4, (y + 1) * width * 4));
  const chunk = (name, payload) => {
    const prefix = Buffer.alloc(8); prefix.writeUInt32BE(payload.length, 0);
    prefix.write(name, 4, "ascii");
    return Buffer.concat([prefix, payload, Buffer.alloc(4)]);
  };
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(Buffer.concat(rows))),
    chunk("IEND", Buffer.alloc(0))
  ]);
}

test("PNG decoder reads Chromium-compatible RGBA scanlines", () => {
  const pixels = Buffer.from([12, 32, 52, 255, 255, 0, 99, 220]);
  assert.deepEqual(decodePng(png(2, 1, pixels)).pixels, pixels);
});

test("pixel comparison catches real differences, allows channel antialiasing", () => {
  const white = decodePng(png(1, 1, Buffer.from([255, 255, 255, 255])));
  const nearWhite = decodePng(png(1, 1, Buffer.from([250, 255, 255, 255])));
  const dark = decodePng(png(1, 1, Buffer.from([20, 30, 40, 255])));
  assert.equal(pixelDifference(white, nearWhite).changed, 0);
  assert.equal(pixelDifference(white, dark).changed, 1);
  assert.equal(pixelDifference(white, decodePng(png(2, 1, Buffer.alloc(8)))).mismatchedSize, true);
});

test("rejects malformed and unsupported PNG data without allocating huge images", () => {
  assert.throws(() => decodePng(Buffer.from("invalid image")));
  assert.throws(() => decodePng(png(1, 1, Buffer.alloc(4), 5)), /Unsupported PNG filter/);
});

test("0.5% visual threshold stays enforced without an explicit approval", () => {
  const under = [{mismatchedSize: false, mismatchPercent: 0.5}];
  const over = [{mismatchedSize: false, mismatchPercent: 0.5001}];
  const resized = [{mismatchedSize: true, mismatchPercent: 0}];
  assert.deepEqual(visualDiffDecision(under), {changed: false, accepted: true});
  assert.deepEqual(visualDiffDecision(over), {changed: true, accepted: false});
  assert.deepEqual(visualDiffDecision(resized), {changed: true, accepted: false});
  assert.deepEqual(visualDiffDecision(over, true), {changed: true, accepted: true});
  assert.deepEqual(visualDiffDecision(resized, true), {changed: true, accepted: true});
  assert.deepEqual(visualDiffDecision(under, true), {changed: false, accepted: true});
});
