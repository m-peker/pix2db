"""Out-of-distribution eval set from TabRecSet (Yang et al., Scientific Data 2023; CC BY 4.0).

English, original (all-line) images only: camera photos, scans, Excel screenshots, invoices, food labels.
Never used for training. Each table is cropped from its image via the cell polygons; the first grid row
is the header (TabRecSet does not mark headers); gold follows the same conventions as htmltable.py.

Usage: python scripts/make_unseen.py --root "RAW/TabRecSet (CurveTabSet)" --out data/unseen_tabrecset --n 150
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.htmltable import html_to_table  # noqa: E402
from pix2db.scene import Scene  # noqa: E402

CATS = ["document image", "excel", "invoice", "ingredints of foods"]


def table_html(cells: list[tuple[int, int, int, int, str]]) -> str:
    rows = collections.defaultdict(list)
    for r, c, rs, cs, t in cells:
        rows[r].append((c, rs, cs, t))
    out = ["<table>"]
    for k, r in enumerate(sorted(rows)):
        tag = "thead" if k == 0 else ("tbody" if k == 1 else None)
        if tag == "tbody":
            out.append("<tbody>")
        if tag == "thead":
            out.append("<thead>")
        out.append("<tr>" + "".join(
            f'<td rowspan="{rs}" colspan="{cs}">{html.escape(t)}</td>' for c, rs, cs, t in sorted(rows[r])) + "</tr>")
        if k == 0:
            out.append("</thead>")
    out.append("</tbody></table>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    files = sorted((root / "TSR_TCR_annotation" / "english").glob("*.json"))
    rng = random.Random(args.seed)
    rng.shuffle(files)
    per_cat = {c: 0 for c in CATS + ["other"]}
    kept = 0
    with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
        for jf in files:
            if kept >= args.n:
                break
            d = json.load(open(jf, encoding="utf-8"))
            cat = next((c for c in CATS if d.get("flags", {}).get(c)), "other")
            img_path = root / "image" / "english_all-line" / d["imagePath"]
            if not img_path.exists():
                continue
            groups = collections.defaultdict(list)
            for s in d["shapes"]:
                parts = s["label"].split("-", 4)
                if len(parts) < 5 or not all(p.isdigit() for p in parts[:4]):
                    continue
                r, c, rs, cs = map(int, parts[:4])
                groups[s.get("group_id")].append(((r, c, rs, cs, " ".join(parts[4].split())), s["points"]))
            for gid, cells in list(groups.items())[:1]:  # one table per image keeps the set diverse
                if kept >= args.n:
                    break
                texts = [t for (_, _, _, _, t), _ in cells]
                if len(cells) < 6 or sum(bool(t) for t in texts) / len(cells) < 0.6:
                    continue  # skip fill-in worksheets with mostly empty cells
                t = html_to_table(table_html([c for c, _ in cells]))
                if t is None:
                    continue
                xs = [p[0] for _, pts in cells for p in pts]
                ys = [p[1] for _, pts in cells for p in pts]
                im = Image.open(img_path).convert("RGB")
                m = 12
                box = (max(0, int(min(xs)) - m), max(0, int(min(ys)) - m),
                       min(im.width, int(max(xs)) + m), min(im.height, int(max(ys)) + m))
                crop = im.crop(box)
                if crop.width < 80 or crop.height < 40:
                    continue
                if crop.width * crop.height > 1400 * 1800:
                    crop.thumbnail((1400, 1800))
                sid = f"trs_{kept:04d}"
                crop.save(out / "images" / f"{sid}.png")
                f.write(json.dumps({"id": sid, "level": 11, "kind": f"tabrecset:{cat}", "size": crop.size,
                                    "source": jf.name, "scene": Scene("tabrecset", [t]).to_dict(),
                                    "num_tol_abs": 0.0}, ensure_ascii=False) + "\n")
                kept += 1
                per_cat[cat] += 1
    print("kept", kept, per_cat)


if __name__ == "__main__":
    main()
