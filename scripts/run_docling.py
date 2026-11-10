"""Docling (TableFormer + OCR) baseline: image -> HTML tables -> SQLite via the same 20-line loader.

Run with /workspace/docling-venv/bin/python. Resumable. Writes <out>/<set>/docling__html.jsonl.
Usage: python scripts/run_docling.py --data data/test data/real_pubtabnet --out runs/rev [--limit 10]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--device", default="cpu", help="cpu keeps the GPU free for training")
    ap.add_argument("--threads", type=int, default=24)
    ap.add_argument("--upscale", type=float, default=1.0, help="resize the image before conversion (helps OCR)")
    ap.add_argument("--tag", default="docling")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    args = ap.parse_args()

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions, TableFormerMode
    from PIL import Image
    from docling.document_converter import DocumentConverter, ImageFormatOption

    opts = PdfPipelineOptions(do_ocr=True, do_table_structure=True)
    opts.ocr_options = EasyOcrOptions(force_full_page_ocr=True)  # images have no text layer
    opts.table_structure_options.mode = TableFormerMode.ACCURATE
    opts.table_structure_options.do_cell_matching = True
    try:
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    except ImportError:
        from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions
    opts.accelerator_options = AcceleratorOptions(num_threads=args.threads,
                                                  device=AcceleratorDevice(args.device))
    conv = DocumentConverter(format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=opts)})

    for data in args.data:
        out = Path(args.out) / Path(data).name
        out.mkdir(parents=True, exist_ok=True)
        path = out / (f"{args.tag}__html.jsonl" if args.num_shards == 1 else f"{args.tag}.part{args.shard:02d}")
        done = set()
        for q in [out / f"{args.tag}__html.jsonl", *out.glob(f"{args.tag}.part*")]:
            if q.exists():
                done |= {json.loads(l)["id"] for l in q.open(encoding="utf-8")}
        items = load_meta(data)[args.shard::args.num_shards]
        todo = [it for it in items if it["id"] not in done][: args.limit]
        print(f"{data}: {len(todo)} to do", flush=True)
        with path.open("a", encoding="utf-8") as f:
            for it in todo:
                t0 = time.time()
                try:
                    src = Path(data) / "images" / f"{it['id']}.png"
                    if args.upscale != 1.0:
                        im = Image.open(src).convert("RGB")
                        im = im.resize((int(im.width * args.upscale), int(im.height * args.upscale)), Image.LANCZOS)
                        src = Path("/tmp") / f"docling_up_{it['id']}.png"
                        im.save(src)
                    doc = conv.convert(src).document
                    if not doc.tables:  # a tight table crop is often laid out as a picture: retry on a page
                        im = Image.open(src).convert("RGB")
                        w, h = im.size
                        page = Image.new("RGB", (int(w * 1.6) + 200, int(h * 1.6) + 200), "white")
                        page.paste(im, ((page.size[0] - w) // 2, (page.size[1] - h) // 2))
                        tmp = Path("/tmp") / f"docling_{it['id']}.png"
                        page.save(tmp)
                        doc = conv.convert(tmp).document
                        tmp.unlink()
                    html = "\n".join(t.export_to_html(doc=doc) for t in doc.tables)
                except Exception as e:  # noqa: BLE001
                    html = f"<!-- error: {e} -->"
                f.write(json.dumps({"id": it["id"], "output": "```html\n" + html + "\n```", "n_tokens": None,
                                    "seconds": time.time() - t0}, ensure_ascii=False) + "\n")
                f.flush()


if __name__ == "__main__":
    main()
