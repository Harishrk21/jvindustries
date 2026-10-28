import Tesseract from "tesseract.js";
import sharp from "sharp";
import fs from "fs";
import path from "path";

const imgPath = process.argv[2];
if (!imgPath || !fs.existsSync(imgPath)) {
  console.error("Usage: node ocr-plate-probe.mjs <image>");
  process.exit(1);
}

const meta = await sharp(imgPath).metadata();
const W = meta.width;
const H = meta.height;
console.log("size", W, "x", H);

async function ocrBuf(buf, label, psm = "6") {
  const r = await Tesseract.recognize(buf, "eng", {
    logger: () => undefined,
    tessedit_pageseg_mode: psm,
    tessedit_char_whitelist: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -",
  });
  const t = (r.data.text || "").trim();
  console.log(`\n=== ${label} psm=${psm} ===`);
  console.log(t || "(empty)");
  return t;
}

async function crop(region) {
  const { left, top, width, height } = region;
  return sharp(imgPath)
    .extract({
      left: Math.max(0, Math.round(left)),
      top: Math.max(0, Math.round(top)),
      width: Math.max(1, Math.round(width)),
      height: Math.max(1, Math.round(height)),
    })
    .resize({ width: 900, withoutEnlargement: false })
    .grayscale()
    .normalize()
    .sharpen()
    .png()
    .toBuffer();
}

const regions = [
  { name: "bottom-center", left: W * 0.28, top: H * 0.72, width: W * 0.44, height: H * 0.26 },
  { name: "bottom-wide", left: W * 0.15, top: H * 0.68, width: W * 0.7, height: H * 0.3 },
  { name: "lower-mid", left: W * 0.2, top: H * 0.55, width: W * 0.6, height: H * 0.35 },
  { name: "plate-tight", left: W * 0.35, top: H * 0.78, width: W * 0.3, height: H * 0.18 },
];

// Yellow-ish mask in lower half
const { data, info } = await sharp(imgPath)
  .ensureAlpha()
  .raw()
  .toBuffer({ resolveWithObject: true });
const yStart = Math.floor(H * 0.55);
let minX = W,
  minY = H,
  maxX = 0,
  maxY = 0,
  count = 0;
for (let y = yStart; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const i = (y * W + x) * info.channels;
    const r = data[i],
      g = data[i + 1],
      b = data[i + 2];
    // commercial yellow plate
    if (r > 160 && g > 120 && b < 110 && r - b > 60 && g - b > 40) {
      count++;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  }
}
console.log("yellow pixels", count, count ? { minX, minY, maxX, maxY } : "none");
if (count > 80) {
  const pad = 12;
  regions.unshift({
    name: "yellow-bbox",
    left: Math.max(0, minX - pad),
    top: Math.max(0, minY - pad),
    width: Math.min(W, maxX - minX + 2 * pad),
    height: Math.min(H, maxY - minY + 2 * pad),
  });
}

const texts = [];
for (const reg of regions) {
  const buf = await crop(reg);
  for (const psm of ["6", "7", "11"]) {
    const t = await ocrBuf(buf, reg.name, psm);
    if (t) texts.push(t);
  }
}

console.log("\n\n======= COMBINED =======");
console.log([...new Set(texts)].join("\n---\n"));
