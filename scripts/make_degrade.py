"""L5 single-degradation study: re-render the L5 test scenes clean, then apply one degradation at a time.

Each variant is a separate set <out>/<variant>/ (images/ + meta.jsonl) with the same gold scenes, so the
only thing that changes between variants is the image degradation.
Usage: python scripts/make_degrade.py --src data/test --out data/degrade [--limit 10]
"""
from __future__ import annotations

import argparse
import io
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.render import Renderer, render_scene, scan_augment  # noqa: E402
from pix2db.scene import Scene  # noqa: E402


def pad(img):
    w, h = img.size
    p = int(0.04 * max(w, h))
    c = Image.new("RGB", (w + 2 * p, h + 2 * p), (235, 233, 228))
    c.paste(img, (p, p))
    return c


def rotate(img, rng):
    return pad(img).rotate(rng.choice([-1, 1]) * 2.5, resample=Image.BICUBIC, expand=True, fillcolor=(210, 208, 204))


def lighting(img, rng):
    a = np.asarray(img).astype(np.float32)
    gx = np.linspace(0.85, 1.05, a.shape[1])[None, :, None]
    gy = np.linspace(1.05, 0.85, a.shape[0])[:, None, None]
    return Image.fromarray(np.clip(a * gx * gy, 0, 255).astype(np.uint8))


def noise(img, rng):
    a = np.asarray(img).astype(np.float32)
    a += np.random.default_rng(rng.randint(0, 2**31)).normal(0, 9, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def blur(img, rng):
    return img.filter(ImageFilter.GaussianBlur(0.9))


def contrast(img, rng):
    return ImageEnhance.Contrast(img).enhance(0.8)


def gray(img, rng):
    return img.convert("L").convert("RGB")


def jpeg(img, rng):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=45)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


# each single degradation at the strongest setting used by scan_augment
VARIANTS = {"clean": [], "rotation": [rotate], "lighting": [lighting], "noise": [noise], "blur": [blur],
            "contrast": [contrast], "grayscale": [gray], "jpeg": [jpeg], "all": "scan"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/test")
    ap.add_argument("--out", default="data/degrade")
    ap.add_argument("--level", type=int, default=5)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    items = [it for it in load_meta(args.src) if it["level"] == args.level][: args.limit]
    outs = {}
    for v in VARIANTS:
        d = Path(args.out) / v
        (d / "images").mkdir(parents=True, exist_ok=True)
        outs[v] = (d / "meta.jsonl").open("w", encoding="utf-8")
    r = Renderer()
    for k, it in enumerate(items):
        scene = Scene.from_dict(it["scene"])
        rng = random.Random(f"degrade-{it['id']}")
        base, _ = render_scene(r, scene, 4, rng)  # same layout family as L5, no degradation
        for v, fns in VARIANTS.items():
            vr = random.Random(f"degrade-{it['id']}-{v}")
            img = scan_augment(base, vr) if fns == "scan" else base
            if fns != "scan":
                for f in fns:
                    img = f(img, vr)
            img.save(Path(args.out) / v / "images" / f"{it['id']}.png")
            m = {k2: it[k2] for k2 in ("id", "level", "kind", "scene", "num_tol_abs") if k2 in it}
            m["size"] = list(img.size)
            m["variant"] = v
            outs[v].write(json.dumps(m, ensure_ascii=False) + "\n")
        if k % 20 == 0:
            print(k, len(items), flush=True)
    r.close()
    for f in outs.values():
        f.close()
    print("done", len(items), "scenes x", len(VARIANTS), "variants")


if __name__ == "__main__":
    main()
