/** Compare real Chromium card screenshots against the PR base in CI.
 * No dependency on image tools: Chrome emits 8-bit RGB/RGBA PNG files.
 */
import {readFile, readdir} from "node:fs/promises";
import {inflateSync} from "node:zlib";
import {resolve} from "node:path";
import {fileURLToPath} from "node:url";

const PNG_MAGIC = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

export function decodePng(input) {
  if (!input.subarray(0, 8).equals(PNG_MAGIC)) throw new Error("Invalid PNG signature");
  let width, height, bitDepth, colorType, interlace;
  let offset = 8;
  const compressed = [];
  while (offset + 12 <= input.length) {
    const length = input.readUInt32BE(offset);
    const kind = input.toString("ascii", offset + 4, offset + 8);
    if (offset + length + 12 > input.length) throw new Error("Truncated PNG chunk");
    const data = input.subarray(offset + 8, offset + 8 + length);
    if (kind === "IHDR") {
      width = data.readUInt32BE(0); height = data.readUInt32BE(4);
      bitDepth = data[8]; colorType = data[9]; interlace = data[12];
    } else if (kind === "IDAT") compressed.push(data);
    else if (kind === "IEND") break;
    offset += 12 + length;
  }
  const channels = colorType === 6 ? 4 : colorType === 2 ? 3 : 0;
  if (!width || !height || width > 2400 || height > 8000 ||
      bitDepth !== 8 || !channels || interlace !== 0 || !compressed.length) {
    throw new Error("Unsupported PNG dimensions or format");
  }
  const stride = width * channels;
  const inflated = inflateSync(Buffer.concat(compressed), {maxOutputLength: (stride + 1) * height});
  if (inflated.length !== (stride + 1) * height) throw new Error("Unexpected PNG scanline length");
  const pixels = Buffer.allocUnsafe(stride * height);
  for (let y = 0; y < height; y++) {
    const base = y * (stride + 1), row = y * stride, filter = inflated[base];
    if (filter > 4) throw new Error("Unsupported PNG filter");
    for (let x = 0; x < stride; x++) {
      const value = inflated[base + 1 + x];
      const left = x >= channels ? pixels[row + x - channels] : 0;
      const up = y > 0 ? pixels[row + x - stride] : 0;
      const upperLeft = y > 0 && x >= channels ? pixels[row + x - stride - channels] : 0;
      let predictor = 0;
      if (filter === 1) predictor = left;
      else if (filter === 2) predictor = up;
      else if (filter === 3) predictor = Math.floor((left + up) / 2);
      else if (filter === 4) {
        const p = left + up - upperLeft;
        const a = Math.abs(p - left), b = Math.abs(p - up), c = Math.abs(p - upperLeft);
        predictor = a <= b && a <= c ? left : b <= c ? up : upperLeft;
      }
      pixels[row + x] = (value + predictor) & 255;
    }
  }
  return {width, height, channels, pixels};
}

export function pixelDifference(a, b, channelTolerance = 16) {
  if (a.width !== b.width || a.height !== b.height) return {changed: Infinity, total: a.width * a.height, mismatchedSize: true};
  let changed = 0;
  const total = a.width * a.height;
  for (let i = 0; i < total; i++) {
    const ai = i * a.channels, bi = i * b.channels;
    let different = false;
    for (let channel = 0; channel < 4; channel++) {
      const av = channel < a.channels ? a.pixels[ai + channel] : 255;
      const bv = channel < b.channels ? b.pixels[bi + channel] : 255;
      if (Math.abs(av - bv) > channelTolerance) different = true;
    }
    if (different) changed++;
  }
  return {changed, total, mismatchPercent: 100 * changed / total, mismatchedSize: false};
}

/** Validate an explicitly reviewed visual migration without lifting the normal limit.
 * A maintainer-controlled PR label enables this mode; image capture, fixture
 * count, decode and all browser/structural checks remain mandatory.
 */
export function visualDiffDecision(differences, approved = false) {
  const changed = differences.some(diff => diff.mismatchedSize || diff.mismatchPercent > 0.5);
  return {changed, accepted: !changed || approved};
}

async function main(baseDirectory, currentDirectory, approval = "") {
  if (!baseDirectory || !currentDirectory || (approval && approval !== "--approved-visual-change")) {
    throw new Error("Usage: node scripts/compare_screenshots.mjs BASE CURRENT [--approved-visual-change]");
  }
  const base = new Set((await readdir(baseDirectory)).filter(file => file.endsWith(".png")));
  const current = new Set((await readdir(currentDirectory)).filter(file => file.endsWith(".png")));
  if (base.size !== 16 || current.size !== 16 || [...base].some(file => !current.has(file))) {
    throw new Error(`Expected 16 matching screenshots, got base=${base.size}, current=${current.size}`);
  }
  const differences = [];
  const maxDifference = 0.5; // Never change the normal visual regression tolerance.
  for (const file of [...base].sort()) {
    const [before, after] = await Promise.all([
      readFile(resolve(baseDirectory, file)), readFile(resolve(currentDirectory, file))
    ]);
    const diff = pixelDifference(decodePng(before), decodePng(after));
    const result = diff.mismatchedSize ? "dimensions changed" : `${diff.mismatchPercent.toFixed(3)}% pixels changed`;
    console.log(`${file}: ${result}`);
    differences.push(diff);
  }
  const decision = visualDiffDecision(differences, approval === "--approved-visual-change");
  if (decision.changed && !decision.accepted) {
    throw new Error(`Card screenshots differ from PR base by more than ${maxDifference}% of pixels or changed dimensions. Review artifacts before applying the visual-change-approved PR label.`);
  }
  if (decision.changed) {
    console.log("::notice title=Reviewed visual redesign::Candidate/base screenshots differ, but the PR carries the visual-change-approved label. All 16 screenshots were still captured and compared. Normal 0.5% tolerance remains active for unapproved PRs.");
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  main(process.argv[2], process.argv[3], process.argv[4]).catch(error => {console.error(error); process.exitCode = 1;});
}
