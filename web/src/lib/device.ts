import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import Tesseract from "tesseract.js";
import type { Gps } from "./api";
import { readGpsSafe, resolveGps, peekCachedGps } from "./gps";

export { readGpsSafe, resolveGps, peekCachedGps };

/** Prefer resolveGps / readGpsSafe — this still throws if device GPS fails with no fallback caller. */
export async function readGps(): Promise<Gps> {
  return readGpsSafe();
}

export async function pickGalleryBlob(fileInput?: HTMLInputElement | null): Promise<Blob> {
  if (fileInput?.files?.[0]) {
    return fileInput.files[0];
  }
  const { Capacitor } = await import("@capacitor/core");
  if (Capacitor.isNativePlatform()) {
    const photo = await Camera.getPhoto({
      quality: 90,
      resultType: CameraResultType.Uri,
      source: CameraSource.Photos,
      correctOrientation: true,
    });
    if (!photo.webPath) throw new Error("Gallery pick failed.");
    const res = await fetch(photo.webPath);
    return res.blob();
  }
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = () => {
      const f = input.files?.[0];
      if (f) resolve(f);
      else reject(new Error("No image selected."));
    };
    input.click();
  });
}

export async function captureLiveBlob(): Promise<Blob> {
  const { Capacitor } = await import("@capacitor/core");
  if (Capacitor.isNativePlatform()) {
    const photo = await Camera.getPhoto({
      quality: 90,
      resultType: CameraResultType.Uri,
      source: CameraSource.Camera,
      correctOrientation: true,
    });
    if (!photo.webPath) throw new Error("Camera capture failed.");
    const res = await fetch(photo.webPath);
    return res.blob();
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" } },
    audio: false,
  });
  try {
    const video = document.createElement("video");
    video.srcObject = stream;
    video.playsInline = true;
    await video.play();
    await new Promise((r) => setTimeout(r, 350));
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas unavailable.");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Capture encode failed."))), "image/jpeg", 0.92);
    });
    return blob;
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}

async function blobToImageBitmap(blob: Blob): Promise<ImageBitmap> {
  return createImageBitmap(blob);
}

function canvasToBlob(canvas: HTMLCanvasElement, type = "image/png"): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, type));
}

type Rect = { x: number; y: number; w: number; h: number };

function isPlateYellow(r: number, g: number, b: number): boolean {
  return r > 150 && g > 110 && b < 120 && r - b > 50 && g - b > 30 && Math.abs(r - g) < 90;
}

/** Find yellow commercial-plate blobs in the lower half (Indian truck ANPR). */
function findYellowPlateRects(img: ImageData, imgW: number, imgH: number): Rect[] {
  const y0 = Math.floor(imgH * 0.5);
  const data = img.data;
  const label = new Int32Array(imgW * imgH);
  let next = 1;
  const parents = [0];
  const find = (a: number): number => {
    while (parents[a] !== a) {
      parents[a] = parents[parents[a]];
      a = parents[a];
    }
    return a;
  };
  const union = (a: number, b: number) => {
    a = find(a);
    b = find(b);
    if (a !== b) parents[b] = a;
  };

  for (let y = y0; y < imgH; y++) {
    for (let x = 0; x < imgW; x++) {
      const i = (y * imgW + x) * 4;
      if (!isPlateYellow(data[i], data[i + 1], data[i + 2])) continue;
      let L = 0;
      if (x > 0 && label[y * imgW + x - 1]) L = label[y * imgW + x - 1];
      if (y > y0 && label[(y - 1) * imgW + x]) {
        const U = label[(y - 1) * imgW + x];
        L = L ? (union(L, U), find(L)) : U;
      }
      if (!L) {
        L = next++;
        parents[L] = L;
      }
      label[y * imgW + x] = L;
    }
  }

  type Box = { minX: number; minY: number; maxX: number; maxY: number; n: number };
  const boxes = new Map<number, Box>();
  for (let y = y0; y < imgH; y++) {
    for (let x = 0; x < imgW; x++) {
      let L = label[y * imgW + x];
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

  const cx0 = imgW / 2;
  return [...boxes.values()]
    .filter((b) => b.n >= 80)
    .map((b) => {
      const w = b.maxX - b.minX + 1;
      const h = b.maxY - b.minY + 1;
      return { x: b.minX, y: b.minY, w, h, n: b.n, ar: w / h, cx: (b.minX + b.maxX) / 2 };
    })
    .filter((b) => b.w >= 36 && b.h >= 16 && b.ar >= 0.85 && b.ar <= 3.8)
    .sort((a, b) => {
      const da = Math.abs(a.cx - cx0);
      const db = Math.abs(b.cx - cx0);
      // Prefer centered, then larger
      return da - db || b.n - a.n;
    })
    .slice(0, 4)
    .map((b) => {
      const padX = Math.round(b.w * 0.14);
      const padY = Math.round(b.h * 0.18);
      const x = Math.max(0, b.x - padX);
      const y = Math.max(0, b.y - padY);
      // Two-line plates need room under the top yellow line (RJ09G over 4017)
      const minH = Math.max(
        b.h + 2 * padY,
        Math.round(b.w * 1.1),
        Math.round(b.h * 2.2),
        90,
      );
      const w = Math.min(imgW - x, Math.max(b.w + 2 * padX, Math.round(b.h * 2.2)));
      const h = Math.min(imgH - y, minH);
      return { x, y, w, h };
    });
}

function bumpFallbackRects(imgW: number, imgH: number): Rect[] {
  return [
    { x: Math.round(imgW * 0.28), y: Math.round(imgH * 0.72), w: Math.round(imgW * 0.44), h: Math.round(imgH * 0.26) },
    { x: Math.round(imgW * 0.32), y: Math.round(imgH * 0.78), w: Math.round(imgW * 0.36), h: Math.round(imgH * 0.2) },
    { x: Math.round(imgW * 0.2), y: Math.round(imgH * 0.58), w: Math.round(imgW * 0.6), h: Math.round(imgH * 0.38) },
  ];
}

async function renderPlateCrop(
  bmp: ImageBitmap,
  rect: Rect,
  mode: "contrast" | "threshold",
  threshold = 140,
): Promise<Blob | null> {
  const scale = Math.max(3, Math.ceil(700 / Math.max(rect.w, 1)));
  const w = Math.round(rect.w * scale);
  const h = Math.round(rect.h * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(bmp, rect.x, rect.y, rect.w, rect.h, 0, 0, w, h);
  const img = ctx.getImageData(0, 0, w, h);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const g = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    let v: number;
    if (mode === "threshold") {
      v = g >= threshold ? 255 : 0;
    } else {
      v = Math.max(0, Math.min(255, (g - 128) * 1.55 + 128));
    }
    d[i] = d[i + 1] = d[i + 2] = v;
  }
  ctx.putImageData(img, 0, 0);
  return canvasToBlob(canvas);
}

async function recognizeText(blob: Blob, psm: string): Promise<string> {
  // tesseract.js v5: pass PSM via createWorker options isn't always honored in recognize();
  // use recognize + tessedit via legacy options bag when supported.
  const result = await Tesseract.recognize(blob, "eng", {
    logger: () => undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ...( { tessedit_pageseg_mode: psm } as any),
  });
  return (result.data.text || "").trim();
}

/** Upscale + contrast helps yellow Indian plates and small bumper text. */
async function preprocessForOcr(blob: Blob): Promise<Blob> {
  try {
    const bmp = await blobToImageBitmap(blob);
    const scale = bmp.width < 1200 ? 2 : 1.25;
    const w = Math.round(bmp.width * scale);
    const h = Math.round(bmp.height * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return blob;
    ctx.drawImage(bmp, 0, 0, w, h);
    const img = ctx.getImageData(0, 0, w, h);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const g = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
      const v = Math.max(0, Math.min(255, (g - 128) * 1.35 + 128));
      d[i] = d[i + 1] = d[i + 2] = v;
    }
    ctx.putImageData(img, 0, 0);
    bmp.close();
    return (await canvasToBlob(canvas)) || blob;
  } catch {
    return blob;
  }
}

function looksPlateish(text: string): boolean {
  const c = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
  // Require full-ish Indian plate shape (not just "IW48" noise)
  return /[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{2,4}/.test(c);
}

function looksPlateWeak(text: string): boolean {
  const c = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return (
    /[A-Z]{2}\d{1,2}/.test(c) ||
    /[A-Z]\d{3,4}/.test(c) ||
    /[A-Z]{2}[A-Z0-9]{2,5}/.test(c) || // APZS / RJO9G OCR scraps
    /[A-Z][A-Z0-9]*\d{2,}/.test(c) // W48S2 / wa8s2
  );
}

export async function ocrBlob(blob: Blob, mode: "general" | "plate" = "general"): Promise<string> {
  if (mode === "plate") {
    return ocrPlateBlob(blob);
  }
  const result = await Tesseract.recognize(blob, "eng", { logger: () => undefined });
  return (result.data.text || "").trim();
}

/**
 * Plate ANPR OCR: crop yellow bumper plates (and bumper fallbacks), threshold,
 * multi-PSM — full-frame OCR alone misses tiny truck plates in truck-art photos.
 */
export async function ocrPlateBlob(blob: Blob): Promise<string> {
  const chunks: string[] = [];
  try {
    const bmp = await blobToImageBitmap(blob);
    const scan = document.createElement("canvas");
    // Cap scan size for CC speed while keeping enough detail for yellow blobs
    const maxSide = 900;
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    scan.width = Math.max(1, Math.round(bmp.width * scale));
    scan.height = Math.max(1, Math.round(bmp.height * scale));
    const sctx = scan.getContext("2d");
    if (!sctx) {
      bmp.close();
      return (await preprocessForOcr(blob).then((b) => recognizeText(b, "6"))) || "";
    }
    sctx.drawImage(bmp, 0, 0, scan.width, scan.height);
    const img = sctx.getImageData(0, 0, scan.width, scan.height);
    const yellow = findYellowPlateRects(img, scan.width, scan.height);
    const fallbacks = bumpFallbackRects(scan.width, scan.height);

    // Map scan rects back to full bitmap coords
    const inv = scale > 0 ? 1 / scale : 1;
    const toFull = (r: Rect): Rect => ({
      x: Math.round(r.x * inv),
      y: Math.round(r.y * inv),
      w: Math.round(r.w * inv),
      h: Math.round(r.h * inv),
    });

    const runRect = async (rect: Rect) => {
      if (rect.w < 20 || rect.h < 12) return;
      // Run several thresholds — first hit is often a digit misread (4017→5015)
      for (const thr of [130, 125, 140, 115] as const) {
        const crop = await renderPlateCrop(bmp, rect, "threshold", thr);
        if (!crop) continue;
        for (const psm of ["6", "7"]) {
          const t = await recognizeText(crop, psm);
          if (t) chunks.push(t);
        }
      }
      const contrast = await renderPlateCrop(bmp, rect, "contrast");
      if (contrast) {
        const t = await recognizeText(contrast, "6");
        if (t) chunks.push(t);
      }
    };

    // Top yellow blobs first (commercial plate colour), then bumper fallbacks
    for (const r of yellow.slice(0, 2)) {
      await runRect(toFull(r));
    }
    if (!chunks.some(looksPlateish) && !chunks.some(looksPlateWeak)) {
      for (const r of fallbacks.slice(0, 2)) {
        await runRect(toFull(r));
      }
    } else if (!chunks.some(looksPlateish)) {
      // Weak scraps only — one bumper pass often completes two-line plates
      await runRect(toFull(fallbacks[0]));
    }

    // Full-frame fallback when crops only produced weak fragments
    if (!chunks.some(looksPlateish) && !chunks.some(looksPlateWeak)) {
      const full = await preprocessForOcr(blob);
      const t = await recognizeText(full, "11");
      if (t) chunks.push(t);
    }

    bmp.close();
  } catch {
    const prepared = await preprocessForOcr(blob);
    return recognizeText(prepared, "6");
  }

  // Deduplicate; if we have strong plate-shaped hits, drop bumper/art noise
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const c of chunks) {
    const key = c.replace(/\s+/g, " ").trim().toUpperCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    unique.push(c);
  }
  const strong = unique.filter(looksPlateish);
  const weak = unique.filter(looksPlateWeak);
  // Keep all plate-shaped + weak scraps so multi-threshold votes (4017 vs 5015) can rank
  if (strong.length || weak.length) {
    return [...new Set([...strong, ...weak])].join("\n");
  }
  return unique.join("\n");
}

/**
 * Shrink JPEG for fast Groq upload (ANPR). Keeps plate readable; cuts transfer + vision latency.
 * Evidence store still receives this same blob from the capture flow.
 */
export async function compressForAnpr(blob: Blob, maxSide = 1280, quality = 0.72): Promise<Blob> {
  try {
    const bmp = await blobToImageBitmap(blob);
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    if (scale >= 0.98 && blob.size < 450_000) {
      bmp.close();
      return blob;
    }
    const w = Math.max(1, Math.round(bmp.width * scale));
    const h = Math.max(1, Math.round(bmp.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      bmp.close();
      return blob;
    }
    ctx.drawImage(bmp, 0, 0, w, h);
    bmp.close();
    const out = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    return out && out.size > 0 ? out : blob;
  } catch {
    return blob;
  }
}
