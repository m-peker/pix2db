"""Generate an image set with gold databases. Sharded and resumable.

Levels: 1 clean · 2 styled · 3 hierarchical · 4 document (FK) · 5 scan · 6 chart · 9 receipt
Usage:
  python scripts/make_set.py --spider DIR [DIR ...] --dbs ids.txt --out data/train \
      --counts 1:2000,2:4000,3:5000,4:5000,5:5000,6:4000 --shard 0 --num-shards 16
Output: <out>/images/<id>.png and <out>/meta_<shard>.jsonl ({id, level, kind, size, scene, num_tol_abs})
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.chart import chart_scene_from, render_chart  # noqa: E402
from pix2db.receipt import receipt_html, sample_receipt  # noqa: E402
from pix2db.render import Renderer, render_scene, scan_augment  # noqa: E402
from pix2db.scene import sample_multi, sample_parent_child, sample_single  # noqa: E402


def pick_kind(level: int, rng: random.Random) -> str:
    r = rng.random()
    if level == 1:
        return "table"
    if level == 2:
        return "table" if r < 0.8 else "multi"
    if level == 3:
        return "table" if r < 0.85 else "multi"
    if level == 4:
        return "doc"
    if level == 5:
        return "table" if r < 0.4 else ("doc" if r < 0.9 else "multi")
    if level == 9:
        return "receipt"
    return "chart"


def sample(kind: str, level: int, db: Path, rng: random.Random):
    if kind == "doc":
        return sample_parent_child(db, rng)
    if kind == "multi":
        return sample_multi(db, rng)
    if kind == "receipt":
        return sample_receipt(rng)
    if kind == "chart":
        s = sample_single(db, rng, n_rows=(3, 12), n_cols=(3, 8))
        return chart_scene_from(s, rng) if s else None
    if level <= 2:
        return sample_single(db, rng, n_rows=(3, 15), n_cols=(3, 7))
    return sample_single(db, rng, n_rows=(4, 25), n_cols=(3, 9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spider", nargs="+", required=True, help="dirs containing <db_id>/<db_id>.sqlite")
    ap.add_argument("--dbs", default=None, help="file with allowed db_ids, one per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--counts", default="1:30,2:30,3:30,4:30,5:30,6:30")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()

    allowed = set(Path(args.dbs).read_text().split()) if args.dbs else None
    dbs = {}
    for d in args.spider:
        for p in sorted(Path(d).glob("*/*.sqlite")):
            if (allowed is None or p.parent.name in allowed) and p.parent.name not in dbs:
                dbs[p.parent.name] = p
    dbs = [dbs[k] for k in sorted(dbs)]
    counts = {int(k): int(v) for k, v in (x.split(":") for x in args.counts.split(","))}

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    meta_path = out / f"meta_{args.shard:03d}.jsonl"
    have = {}
    if meta_path.exists():
        for l in meta_path.open(encoding="utf-8"):
            lv = json.loads(l)["level"]
            have[lv] = have.get(lv, 0) + 1
    print(f"shard {args.shard}: {len(dbs)} databases, existing {have}", flush=True)

    renderer = None
    with meta_path.open("a", encoding="utf-8") as fout:
        for level, total in sorted(counts.items()):
            # this shard's share of the level
            n = total // args.num_shards + (1 if args.shard < total % args.num_shards else 0)
            rng = random.Random(f"{args.seed}-{level}-{args.shard}")
            made = have.get(level, 0)
            # replay rng for resumability is not exact; use a fresh stream offset by `made`
            rng.seed(f"{args.seed}-{level}-{args.shard}-{made}")
            tries = 0
            while made < n and tries < n * 30 + 100:
                tries += 1
                db = rng.choice(dbs)
                kind = pick_kind(level, rng)
                scene = sample(kind, level, db, rng)
                if scene is None:
                    continue
                sid = f"{args.prefix}s{args.shard:03d}_L{level}_{made:05d}"
                extra = {"num_tol_abs": 0.0}
                if kind == "receipt":
                    scene, info = scene
                    if renderer is None:
                        renderer = Renderer()
                    img = renderer.png(receipt_html(scene, info, rng))
                    if rng.random() < 0.85:
                        img = scan_augment(img, rng)
                elif kind == "chart":
                    img, info = render_chart(scene, rng)
                    extra.update(info)
                    if rng.random() < 0.2:
                        img = scan_augment(img, rng)
                else:
                    if renderer is None:
                        renderer = Renderer()
                    img, _ = render_scene(renderer, scene, level, rng)
                if img.size[0] * img.size[1] > 1400 * 1800:  # too large for a sensible token budget
                    continue
                img.save(out / "images" / f"{sid}.png", optimize=False)
                fout.write(json.dumps({"id": sid, "level": level, "kind": kind, "size": img.size,
                                       "scene": scene.to_dict(), **extra}, ensure_ascii=False) + "\n")
                fout.flush()
                made += 1
            print(f"shard {args.shard} level {level}: {made}/{n} ({tries} tries)", flush=True)
    if renderer:
        renderer.close()


if __name__ == "__main__":
    main()
