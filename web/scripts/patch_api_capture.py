from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "lib" / "api.ts"
t = p.read_text(encoding="utf-8")
if "export type CaptureSource" not in t:
    t = t.replace(
        "export type Gps = { lat: number; lon: number; accuracy_m: number };",
        'export type Gps = { lat: number; lon: number; accuracy_m: number };\n\n'
        'export type CaptureSource = "LIVE_CAMERA" | "OWNER_GALLERY_UPLOAD";',
    )
old = 'fd.append("capture_source", "LIVE_CAMERA");'
new = 'fd.append("capture_source", args.captureSource || "LIVE_CAMERA");'
n = t.count(old)
t = t.replace(old, new)
# Add captureSource?: CaptureSource to arg objects that have blob: Blob
# Heuristic: after "blob: Blob;" insert optional field if missing nearby
import re

def add_field(m: re.Match[str]) -> str:
    block = m.group(0)
    if "captureSource" in block:
        return block
    return block.replace("blob: Blob;", "blob: Blob;\n    captureSource?: CaptureSource;")

t = re.sub(
    r"args:\s*\{[^}]*blob:\s*Blob;[^}]*\}",
    add_field,
    t,
    flags=re.S,
)
p.write_text(t, encoding="utf-8")
print(f"capture_source lines replaced: {n}")
