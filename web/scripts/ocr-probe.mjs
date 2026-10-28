import Tesseract from "tesseract.js";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const img = process.argv[2];
if (!img || !fs.existsSync(img)) {
  console.error("Usage: node ocr-probe.mjs <image>");
  process.exit(1);
}

console.log("OCR:", path.basename(img), fs.statSync(img).size, "bytes");

const r = await Tesseract.recognize(img, "eng", {
  logger: (m) => {
    if (m.status === "recognizing text" && m.progress != null) {
      process.stdout.write(`\rrecog ${(m.progress * 100).toFixed(0)}%`);
    }
  },
});
console.log("\n--- FULL FRAME ---");
console.log(r.data.text);
console.log("confidence", r.data.confidence);

// Second pass with sparse text
const r2 = await Tesseract.recognize(img, "eng", {
  logger: () => undefined,
  tessedit_pageseg_mode: "11",
});
console.log("\n--- PSM 11 ---");
console.log(r2.data.text);
