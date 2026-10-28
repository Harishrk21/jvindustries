/** Mimics device.ts yellow-plate OCR → backend parser. */
import Tesseract from "tesseract.js";
import sharp from "sharp";
import { spawnSync } from "child_process";

const imgPath = process.argv[2];
if (!imgPath) process.exit(1);

const meta = await sharp(imgPath).metadata();
const W = meta.width;
const H = meta.height;

function isYellow(r, g, b) {
  return r > 150 && g > 110 && b < 120 && r - b > 50 && g - b > 30 && Math.abs(r - g) < 90;
}

const { data, info } = await sharp(imgPath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
const ch = info.channels;
const y0 = Math.floor(H * 0.5);
const label = new Int32Array(W * H);
let next = 1;
const parents = [0];
const find = (a) => {
  while (parents[a] !== a) a = parents[a] = parents[parents[a]];
  return a;
};
const union = (a, b) => {
  a = find(a);
  b = find(b);
  if (a !== b) parents[b] = a;
};
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
const cx0 = W / 2;
const yellow = [...boxes.values()]
  .filter((b) => b.n >= 80)
  .map((b) => {
    const w = b.maxX - b.minX + 1;
    const h = b.maxY - b.minY + 1;
    return { x: b.minX, y: b.minY, w, h, n: b.n, ar: w / h, cx: (b.minX + b.maxX) / 2 };
  })
  .filter((b) => b.w >= 36 && b.h >= 16 && b.ar >= 0.85 && b.ar <= 3.8)
  .sort((a, b) => Math.abs(a.cx - cx0) - Math.abs(b.cx - cx0) || b.n - a.n)
  .slice(0, 2)
  .map((b) => {
    const padX = Math.round(b.w * 0.14);
    const padY = Math.round(b.h * 0.18);
    const x = Math.max(0, b.x - padX);
    const y = Math.max(0, b.y - padY);
    const minH = Math.max(b.h + 2 * padY, Math.round(b.w * 1.1), Math.round(b.h * 2.2), 90);
    const w = Math.min(W - x, Math.max(b.w + 2 * padX, Math.round(b.h * 2.2)));
    const h = Math.min(H - y, minH);
    return { x, y, w, h };
  });

console.log("yellow crops", yellow);

const chunks = [];
function plateish(t) {
  const c = t.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return /[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{2,4}/.test(c);
}
function plateWeak(t) {
  const c = t.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return (
    /[A-Z]{2}\d{1,2}/.test(c) ||
    /[A-Z]\d{3,4}/.test(c) ||
    /[A-Z]{2}[A-Z0-9]{2,5}/.test(c) ||
    /[A-Z][A-Z0-9]*\d{2,}/.test(c)
  );
}

for (const rect of yellow) {
  for (const thr of [130, 125, 140, 115, 120]) {
    const buf = await sharp(imgPath)
      .extract({ left: rect.x, top: rect.y, width: rect.w, height: rect.h })
      .resize({ width: 700 })
      .grayscale()
      .normalize()
      .threshold(thr)
      .png()
      .toBuffer();
    for (const psm of ["6", "7"]) {
      const r = await Tesseract.recognize(buf, "eng", { logger: () => undefined, tessedit_pageseg_mode: psm });
      const t = (r.data.text || "").trim();
      if (t) {
        chunks.push(t);
        console.log(`thr${thr}/psm${psm}`, JSON.stringify(t));
      }
    }
  }
}

const unique = [...new Set(chunks.map((c) => c.replace(/\s+/g, " ").trim()))].filter(Boolean);
const strong = unique.filter(plateish);
const weak = unique.filter(plateWeak);
const ocrText = (strong.length ? strong : weak.length ? weak : unique).join("\n");
console.log("SEND:\n", ocrText);

const py = `
from app.ai.vehicle_recognition import get_vehicle_recognition_service
import sys
text = sys.stdin.read()
r = get_vehicle_recognition_service().recognize_from_ocr(ocr_text=text)
print(r.value or 'NONE', round(r.confidence,2), r.failed, r.candidates[:4])
`;
const res = spawnSync("D:/mobile-app-jv/backend/.venv/Scripts/python.exe", ["-c", py], {
  input: ocrText,
  encoding: "utf-8",
  cwd: "D:/mobile-app-jv/backend",
});
console.log("PARSER:", res.stdout.trim() || res.stderr);
