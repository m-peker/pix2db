"""Fast batched inference with vLLM (run with /workspace/vllm-venv/bin/python). Resumable.

Usage: python scripts/infer_vllm.py --data data/test --model MODEL_OR_DIR --prompt sql --out runs/test --tag NAME
Writes <out>/<tag>__<prompt>.jsonl with {id, output, n_tokens, seconds} (same format as infer.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.prompts import PROMPTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", required=True, help="one or more data dirs")
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", choices=list(PROMPTS), default="sql")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=3072)
    ap.add_argument("--max-pixels", type=int, default=1310720)
    ap.add_argument("--gpu-mem", type=float, default=0.85)
    args = ap.parse_args()

    from transformers import AutoProcessor
    from vllm import LLM, SamplingParams

    tag = args.tag or Path(args.model).name
    processor = AutoProcessor.from_pretrained(args.model)
    llm = LLM(model=args.model, max_model_len=8192, limit_mm_per_prompt={"image": 1},
              mm_processor_kwargs={"max_pixels": args.max_pixels}, gpu_memory_utilization=args.gpu_mem,
              seed=42)
    sp = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)
    text = processor.apply_chat_template(
        [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPTS[args.prompt]}]}],
        tokenize=False, add_generation_prompt=True)

    for data in args.data:
        out = Path(args.out) / Path(data).name
        out.mkdir(parents=True, exist_ok=True)
        out_path = out / f"{tag}__{args.prompt}.jsonl"
        done = {json.loads(l)["id"] for l in out_path.open(encoding="utf-8")} if out_path.exists() else set()
        todo = [it for it in load_meta(data) if it["id"] not in done]
        print(f"{data}: {len(todo)} to do -> {out_path}", flush=True)
        if not todo:
            continue
        reqs = [{"prompt": text, "multi_modal_data": {
            "image": Image.open(Path(data) / "images" / f"{it['id']}.png").convert("RGB")}} for it in todo]
        t0 = time.time()
        res = llm.generate(reqs, sp)
        dt = (time.time() - t0) / len(todo)
        with out_path.open("a", encoding="utf-8") as f:
            for it, r in zip(todo, res):
                o = r.outputs[0]
                f.write(json.dumps({"id": it["id"], "output": o.text, "n_tokens": len(o.token_ids),
                                    "seconds": dt}, ensure_ascii=False) + "\n")
        print(f"  done, {dt:.2f}s/image (amortized)", flush=True)


if __name__ == "__main__":
    main()
