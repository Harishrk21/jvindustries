from pathlib import Path

root = Path(__file__).resolve().parents[1] / "src" / "pages"
for path in root.glob("*.tsx"):
    text = path.read_text(encoding="utf-8")
    # Count Link usages outside import lines
    uses = 0
    for line in text.splitlines():
        if line.strip().startswith("import "):
            continue
        uses += line.count("Link")
    if uses > 0:
        continue
    orig = text
    text = text.replace('import { Link } from "react-router-dom";\n', "")
    text = text.replace(
        'import { Link, useParams } from "react-router-dom";',
        'import { useParams } from "react-router-dom";',
    )
    text = text.replace(
        'import { Link, useNavigate } from "react-router-dom";',
        'import { useNavigate } from "react-router-dom";',
    )
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print("fixed", path.name)
