"""Merge a LoRA adapter into its base model and save a standalone model (for vLLM / HF release).

Usage: python scripts/merge_lora.py --base Qwen/Qwen3-VL-2B-Instruct --adapter CKPT/final --out OUT_DIR
"""
import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    model = AutoModelForImageTextToText.from_pretrained(args.base, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, args.adapter).merge_and_unload()
    model.save_pretrained(args.out, safe_serialization=True)
    AutoProcessor.from_pretrained(args.base).save_pretrained(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()
