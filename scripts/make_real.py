"""Build small real-image evaluation sets with gold databases.

  pubtabnet : real tables cropped from scientific PDFs (apoidea/pubtabnet-html, val split).
              Only tables without row/col spans and with one header row, so the gold is unambiguous.
  cord      : real receipt photos (naver-clova-ix/cord-v2, test split). Gold = line-item table
              (name, quantity, price). Extra tables (e.g. receipt totals) are allowed: use recall.

Usage: python scripts/make_real.py --which pubtabnet --out data/real_pubtabnet --n 150
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.scene import Column, Scene, Table, coerce_column, infer_type, snake  # noqa: E402

MINUS = str.maketrans({"−": "-", "–": "-", " ": " ", " ": " "})


def clean_text(s: str) -> str | None:
    s = re.sub(r"<[^>]+>", "", s).translate(MINUS)
    s = " ".join(s.split())
    return s or None


def pubtabnet(n: int, rng: random.Random, out: Path):
    from bs4 import BeautifulSoup
    from datasets import load_dataset

    ds = load_dataset("apoidea/pubtabnet-html", split="validation", streaming=True)
    kept = 0
    with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
        for ex in ds:
            if kept >= n:
                break
            if rng.random() > 0.35:  # thin the stream for variety
                continue
            soup = BeautifulSoup(ex["html_table"], "html.parser")
            if soup.find(attrs={"rowspan": True}) or soup.find(attrs={"colspan": True}):
                continue
            thead, tbody = soup.find("thead"), soup.find("tbody")
            if not thead or not tbody or len(thead.find_all("tr")) != 1:
                continue
            head = [clean_text(c.get_text(" ")) for c in thead.find("tr").find_all(["td", "th"])]
            rows = [[clean_text(c.get_text(" ")) for c in tr.find_all(["td", "th"])] for tr in tbody.find_all("tr")]
            if not (2 <= len(head) <= 8 and 3 <= len(rows) <= 20) or any(len(r) != len(head) for r in rows):
                continue
            if head[0] is None:
                head[0] = "item"
            if any(h is None for h in head) or any(all(v is None for v in r) for r in rows):
                continue
            names = [snake(h) for h in head]
            if len(set(names)) != len(names):
                continue
            cols = list(zip(*rows))
            cols = [coerce_column(list(c)) for c in cols]
            rows = [list(r) for r in zip(*cols)]
            table = Table("table_1", [Column(nm, infer_type(list(c))) for nm, c in zip(names, cols)], rows)
            sid = f"ptn_{kept:04d}"
            ex["image"].convert("RGB").save(out / "images" / f"{sid}.png")
            f.write(json.dumps({"id": sid, "level": 7, "kind": "real_table", "size": ex["image"].size,
                                "scene": Scene("pubtabnet", [table]).to_dict(), "num_tol_abs": 0.0},
                               ensure_ascii=False) + "\n")
            kept += 1
    print("pubtabnet kept", kept)


def num_id(s):
    """Receipt numbers: '60.000' / '28,000' (thousand separators) -> 60000 / 28000."""
    if s is None:
        return None
    t = s.strip().replace(" ", "")
    neg = t.startswith("-")
    t = t.lstrip("-")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", t):
        v = int(re.sub(r"[.,]", "", t))
    elif re.fullmatch(r"\d+", t):
        v = int(t)
    elif re.fullmatch(r"\d+[.,]\d{1,2}", t):
        v = float(t.replace(",", "."))
    else:
        return s
    return -v if neg else v


def cord(n: int, rng: random.Random, out: Path):
    from datasets import load_dataset

    ds = load_dataset("naver-clova-ix/cord-v2", split="test")
    idx = list(range(len(ds)))
    rng.shuffle(idx)
    kept = 0
    with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
        for i in idx:
            if kept >= n:
                break
            ex = ds[i]
            gp = json.loads(ex["ground_truth"])["gt_parse"]
            menu = gp.get("menu", [])
            menu = [menu] if isinstance(menu, dict) else menu
            rows = []
            for m in menu:
                if not isinstance(m, dict) or "nm" not in m or "price" not in m:
                    continue
                nm = m["nm"] if isinstance(m["nm"], str) else " ".join(map(str, m["nm"]))
                cnt = m.get("cnt")
                cnt = num_id(re.sub(r"[xX]$", "", cnt).strip()) if isinstance(cnt, str) else None
                rows.append([clean_text(nm), cnt, num_id(m["price"]) if isinstance(m["price"], str) else None])
            if len(rows) < 2:
                continue
            cols = [coerce_column(list(c)) for c in zip(*rows)]
            rows = [list(r) for r in zip(*cols)]
            names = ["item_name", "quantity", "price"]
            table = Table("items", [Column(nm, infer_type(list(c))) for nm, c in zip(names, cols)], rows)
            sid = f"cord_{kept:04d}"
            img = ex["image"].convert("RGB")
            if img.size[0] * img.size[1] > 1400 * 1800:
                img.thumbnail((1400, 1800))
            img.save(out / "images" / f"{sid}.png")
            f.write(json.dumps({"id": sid, "level": 8, "kind": "real_receipt", "size": img.size,
                                "scene": Scene("cord", [table]).to_dict(), "num_tol_abs": 0.0,
                                "recall_only": True}, ensure_ascii=False) + "\n")
            kept += 1
    print("cord kept", kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", choices=["pubtabnet", "cord"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    {"pubtabnet": pubtabnet, "cord": cord}[args.which](args.n, rng, out)


if __name__ == "__main__":
    main()
