import Tesseract from "tesseract.js";
import sharp from "sharp";
import fs from "fs";

const imgPath = process.argv[2];
const meta = await sharp(imgPath).metadata();
const W = meta.width;
const H = meta.height;
console.log("size", W, "x", H);

const { data, info } = await sharp(imgPath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
const ch = info.channels;

function isYellow(r, g, b) {
  return r > 150 && g > 110 && b < 120 && r - b > 50 && g - b > 30 && Math.abs(r - g) < 90;
}

// Connected components of yellow in lower 45%
const y0 = Math.floor(H * 0.55);
const label = new Int32Array(W * H);
let next = 1;
const parents = [0];
function find(a) {
  while (parents[a] !== a) a = parents[a] = parents[parents[a]];
  return a;
}
function union(a, b) {
  a = find(a);
  b = find(b);
  if (a !== b) parents[b] = a;
}

for (let y = y0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const i = (y * W + x) * ch;
    if (!isYellow(data[i], data[i + 1], data[i + 2])) continue;
    let L = 0;
    if (x > 0 && label[y * W + x - 1]) L = label[y * W + x - 1];
    if (y > y0 && label[(y - 1) * W + x]) {
      const U = label[(y - 1) * W + x];
      L = L ? (union(L, U), find(L)) : U;
    }
    if (!L) {
      L = next++;
      parents[L] = L;
    }
    label[y * W + x] = L;
  }
}

const boxes = new Map();
for (let y = y0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    let L = label[y * W + x];
    if (!L) continue;
    L = find(L);
    let b = boxes.get(L);
    if (!b) {
      b = { minX: x, minY: y, maxX: x, maxY: y, n: 0 };
      boxes.set(L, b);
    }
    b.n++;
    if (x < b.minX) b.minX = x;
    if (y < b.minY) b.minY = y;
    if (x > b.maxX) b.maxX = x;
    if (y > b.maxY) b.maxY = y;
  }
}

const candidates = [...boxes.values()]
  .filter((b) => b.n >= 80)
  .map((b) => {
    const w = b.maxX - b.minX + 1;
    const h = b.maxY - b.minY + 1;
    return { ...b, w, h, ar: w / h };
  })
  .filter((b) => b.w >= 40 && b.h >= 20 && b.ar >= 0.9 && b.ar <= 3.5)
  .sort((a, b) => b.n - a.n);

console.log(
  "yellow blobs",
  candidates.slice(0, 8).map((b) => ({ n: b.n, w: b.w, h: b.h, ar: +b.ar.toFixed(2), x: b.minX, y: b.minY })),
);

async function prep(extract, opts = {}) {
  let p = sharp(imgPath).extract(extract).resize({ width: opts.width || 800, withoutEnlargement: false });
  if (opts.threshold != null) {
    p = p.grayscale().normalize().threshold(opts.threshold);
  } else {
    p = p.grayscale().normalize().modulate({ brightness: 1.05 }).sharpen();
  }
  return p.png().toBuffer();
}

async function run(buf, label, psm) {
  const r = await Tesseract.recognize(buf, "eng", {
    logger: () => undefined,
    tessedit_pageseg_mode: psm,
  });
  const t = (r.data.text || "").replace(/[^\w\s\-]/g, " ").replace(/\s+/g, " ").trim();
  console.log(`[${label} psm${psm}]`, t || "(empty)");
  return t;
}

const regions = [];
for (const b of candidates.slice(0, 5)) {
  const padX = Math.round(b.w * 0.12);
  const padY = Math.round(b.h * 0.15);
  regions.push({
    name: `blob-${b.minX},${b.minY}`,
    left: Math.max(0, b.minX - padX),
    top: Math.max(0, b.minY - padY),
    width: Math.min(W - Math.max(0, b.minX - padX), b.w + 2 * padX),
    height: Math.min(H - Math.max(0, b.minY - padY), b.h + 2 * padY),
  });
}
// Forced bumper plate hang zone (between wheels)
regions.push({
  name: "hang-plate",
  left: Math.round(W * 0.32),
  top: Math.round(H * 0.82),
  width: Math.round(W * 0.36),
  height: Math.round(H * 0.16),
});
regions.push({
  name: "hang-plate-hi",
  left: Math.round(W * 0.3),
  top: Math.round(H * 0.78),
  width: Math.round(W * 0.4),
  height: Math.round(H * 0.2),
});

const outDir = "D:/mobile-app-jv/tmp-ocr/crops";
fs.mkdirSync(outDir, { recursive: true });

for (const reg of regions) {
  const extract = {
    left: reg.left,
    top: reg.top,
    width: Math.min(reg.width, W - reg.left),
    height: Math.min(reg.height, H - reg.top),
  };
  if (extract.width < 10 || extract.height < 10) continue;
  const bufN = await prep(extract);
  const bufT = await prep(extract, { threshold: 140 });
  fs.writeFileSync(`${outDir}/${pathBase(reg.name)}_n.png`, bufN);
  fs.writeFileSync(`${outDir}/${pathBase(reg.name)}_t.png`, bufT);
  for (const psm of ["6", "7", "8", "11"]) {
    await run(bufN, reg.name + "/norm", psm);
    await run(bufT, reg.name + "/thr", psm);
  }
}

function pathBase(s) {
  return s.replace(/[^a-zA-Z0-9_-]+/g, "_");
}
