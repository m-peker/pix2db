"""Zero-shot (or fine-tuned) inference with a Hugging Face VLM. Resumable, cached per id.

Usage: python scripts/infer.py --data data/feas --model Qwen/Qwen3-VL-4B-Instruct --prompt sql \
           --out runs/feas [--limit 10] [--batch 8]
Writes <out>/<model_tag>__<prompt>.jsonl with {id, output, n_tokens, seconds}.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.prompts import PROMPTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None, help="optional LoRA adapter dir")
    ap.add_argument("--prompt", choices=list(PROMPTS), default="sql")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=3072)
    ap.add_argument("--max-pixels", type=int, default=1280 * 28 * 28)
    args = ap.parse_args()

    torch.manual_seed(42)
    tag = args.tag or args.model.split("/")[-1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / f"{tag}__{args.prompt}.jsonl"
    done = set()
    if out_path.exists():
        done = {json.loads(l)["id"] for l in out_path.open(encoding="utf-8")}

    items = load_meta(args.data)
    if args.limit:
        # take the first N of every level so smoke tests cover all levels
        by_level = {}
        for it in items:
            by_level.setdefault(it["level"], []).append(it)
        items = [it for lv in sorted(by_level) for it in by_level[lv][: args.limit]]
    todo = [it for it in items if it["id"] not in done]
    print(f"{len(items)} items, {len(todo)} to do -> {out_path}")
    if not todo:
        return

    processor = AutoProcessor.from_pretrained(args.model, max_pixels=args.max_pixels)
    processor.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    prompt = PROMPTS[args.prompt]

    # longest images first keeps padding waste low within a batch
    todo.sort(key=lambda it: -(it["size"][0] * it["size"][1]))
    with out_path.open("a", encoding="utf-8") as fout:
        for b in range(0, len(todo), args.batch):
            batch = todo[b: b + args.batch]
            msgs = [[{"role": "user", "content": [
                {"type": "image", "image": Image.open(Path(args.data) / "images" / f"{it['id']}.png").convert("RGB")},
                {"type": "text", "text": prompt}]}] for it in batch]
            inputs = processor.apply_chat_template(
                msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                return_tensors="pt", padding=True).to(model.device)
            t0 = time.time()
            with torch.inference_mode():
                gen = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
            dt = time.time() - t0
            gen = gen[:, inputs["input_ids"].shape[1]:]
            texts = processor.batch_decode(gen, skip_special_tokens=True)
            pad = processor.tokenizer.pad_token_id
            for it, txt, g in zip(batch, texts, gen):
                n = int((g != pad).sum())
                fout.write(json.dumps({"id": it["id"], "output": txt, "n_tokens": n,
                                       "seconds": dt / len(batch)}, ensure_ascii=False) + "\n")
            fout.flush()
            print(f"  {b + len(batch)}/{len(todo)}  {dt:.1f}s", flush=True)


if __name__ == "__main__":
    main()
