"""LoRA fine-tuning of a Qwen3-VL model on image → SQLite dump.

Usage: python scripts/train.py --config configs/train_2b.yaml [--max-steps 20]   # smoke test
Loss is computed only on the assistant answer (the ```sql block). Vision tower frozen.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import torch
import yaml
from PIL import Image
from torch.utils.data import Dataset
from transformers import AutoModelForImageTextToText, AutoProcessor, Trainer, TrainingArguments

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.prompts import SQL_PROMPT  # noqa: E402
from pix2db.scene import Scene  # noqa: E402


def target_text(item: dict) -> str:
    return "```sql\n" + Scene.from_dict(item["scene"]).to_sql() + "\n```"


class SqlDataset(Dataset):
    """A mixture of generated sets.

    sources: list of {dir, n (max items, optional), kinds (optional filter), repeat (optional, default 1)}
    or a single directory string (v1 configs).
    """

    def __init__(self, sources, limit: int | None = None, seed: int = 42):
        if isinstance(sources, str):
            sources = [{"dir": sources}]
        rng = random.Random(seed)
        self.items = []
        for src in sources:
            items = load_meta(src["dir"])
            if src.get("kinds"):
                items = [it for it in items if it["kind"] in src["kinds"]]
            rng.shuffle(items)
            if src.get("n"):
                items = items[: src["n"]]
            for it in items:
                it["_dir"] = src["dir"]
            self.items += items * int(src.get("repeat", 1))
            print(f"  source {src['dir']} {src.get('kinds', '')}: {len(items)} x{src.get('repeat', 1)}")
        rng.shuffle(self.items)
        if limit:
            self.items = self.items[:limit]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        it = self.items[i]
        img = Image.open(Path(it["_dir"]) / "images" / f"{it['id']}.png").convert("RGB")
        return {"image": img, "target": target_text(it)}


class Collator:
    def __init__(self, processor, max_len: int):
        self.p = processor
        self.max_len = max_len
        tok = processor.tokenizer
        self.assistant_ids = tok.encode("<|im_start|>assistant\n", add_special_tokens=False)
        self.pad_id = tok.pad_token_id

    def __call__(self, batch):
        msgs = [[{"role": "user", "content": [{"type": "image", "image": b["image"]},
                                              {"type": "text", "text": SQL_PROMPT}]},
                 {"role": "assistant", "content": [{"type": "text", "text": b["target"]}]}] for b in batch]
        enc = self.p.apply_chat_template(msgs, tokenize=True, return_dict=True, return_tensors="pt",
                                         padding=True, add_generation_prompt=False)
        ids = enc["input_ids"]
        labels = torch.full_like(ids, -100)
        a = torch.tensor(self.assistant_ids)
        for r in range(ids.size(0)):
            row = ids[r]
            start = None
            for k in range(row.size(0) - len(a), -1, -1):  # last assistant marker
                if torch.equal(row[k:k + len(a)], a):
                    start = k + len(a)
                    break
            if start is None:
                continue
            labels[r, start:] = row[start:]
        labels[ids == self.pad_id] = -100
        if "attention_mask" in enc:
            labels[enc["attention_mask"] == 0] = -100
        enc["labels"] = labels
        if ids.size(1) > self.max_len:
            # never truncate image tokens; drop the batch's tail instead (rare, logged)
            print(f"[warn] batch length {ids.size(1)} > max_len {self.max_len}", flush=True)
        return dict(enc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    torch.manual_seed(cfg.get("seed", 42))

    processor = AutoProcessor.from_pretrained(cfg["model"], max_pixels=cfg["max_pixels"])
    processor.tokenizer.padding_side = "right"
    model = AutoModelForImageTextToText.from_pretrained(cfg["model"], dtype=torch.bfloat16,
                                                       attn_implementation="sdpa")
    from peft import LoraConfig, get_peft_model
    lcfg = LoraConfig(r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"],
                      target_modules=cfg["target_modules"], task_type="CAUSAL_LM")
    model = get_peft_model(model, lcfg)
    model.print_trainable_parameters()
    if cfg.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()

    train = SqlDataset(cfg.get("train_sources") or cfg["train_dir"], limit=args.limit)
    print(f"train items: {len(train)}")
    targs = TrainingArguments(
        output_dir=cfg["output_dir"],
        per_device_train_batch_size=cfg["batch_size"],
        gradient_accumulation_steps=cfg["grad_accum"],
        learning_rate=cfg["lr"],
        lr_scheduler_type="cosine",
        warmup_steps=cfg.get("warmup_ratio", 0.03),  # transformers 5: float < 1 = ratio
        num_train_epochs=cfg["epochs"],
        max_steps=args.max_steps or -1,
        bf16=True,
        logging_steps=10,
        save_steps=cfg.get("save_steps", 500),
        save_total_limit=3,
        dataloader_num_workers=8,
        remove_unused_columns=False,
        report_to="none",
        seed=cfg.get("seed", 42),
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train,
                      data_collator=Collator(processor, cfg.get("max_len", 4096)))
    ckpts = sorted(Path(cfg["output_dir"]).glob("checkpoint-*"))
    trainer.train(resume_from_checkpoint=bool(ckpts) and not args.max_steps)
    final = Path(cfg["output_dir"]) / "final"
    model.save_pretrained(final)
    processor.save_pretrained(final)
    print(f"saved {final}")


if __name__ == "__main__":
    main()
