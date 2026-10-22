---
license: apache-2.0
base_model: Qwen/Qwen3-VL-2B-Instruct
pipeline_tag: image-text-to-text
library_name: transformers
datasets:
  - musapeker/pix2db-data
language:
  - en
tags:
  - table-extraction
  - text-to-sql
  - sqlite
  - document-understanding
  - receipts
  - invoices
  - charts
---

# pix2db-2b — image → working SQLite database

A 2B vision-language model that turns a screenshot or photo of a **table, form, invoice, receipt or chart**
into a **SQLite dump that runs**: `CREATE TABLE` with types and keys, `FOREIGN KEY`s between related tables
(e.g. invoice header ↔ line items), and `INSERT`s for every row. Merged cells are expanded, multi-level headers
flattened, thousand separators / currency / accounting negatives normalized, dates written as ISO.

Code, repair layer and evaluation: **https://github.com/m-peker/pix2db** ·
Demo: [Space](https://huggingface.co/spaces/musapeker/pix2db) ·
[Colab](https://colab.research.google.com/github/m-peker/pix2db/blob/main/notebooks/pix2db_colab.ipynb)

## Usage

With the `pix2db` package (adds the verify/repair layer and a real SQLite database):

```python
# pip install "git+https://github.com/m-peker/pix2db"
from pix2db import Pix2DB

model = Pix2DB.from_pretrained("musapeker/pix2db-2b")
db = model.extract("invoice.png")
print(db.sql)
db.query("SELECT SUM(price) FROM line_items")
db.save("invoice.sqlite")
```

With plain `transformers` (raw SQL text):

```python
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from pix2db.prompts import SQL_PROMPT   # or copy the prompt from the repo

proc = AutoProcessor.from_pretrained("musapeker/pix2db-2b")
model = AutoModelForImageTextToText.from_pretrained("musapeker/pix2db-2b", dtype=torch.bfloat16, device_map="auto")
msgs = [{"role": "user", "content": [{"type": "image", "image": "invoice.png"}, {"type": "text", "text": SQL_PROMPT}]}]
inputs = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                  return_tensors="pt").to(model.device)
out = model.generate(**inputs, max_new_tokens=3072, do_sample=False)
print(proc.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

The model was trained with this exact instruction (`SQL_PROMPT`); other prompts work less well.

### LoRA adapter

The repo root holds the merged model. The LoRA adapter it was merged from is in `adapter/`
(280 MB) — useful if you want to keep fine-tuning on your own documents:

```python
from peft import PeftModel
from transformers import AutoModelForImageTextToText
base = AutoModelForImageTextToText.from_pretrained("Qwen/Qwen3-VL-2B-Instruct", dtype="auto", device_map="auto")
model = PeftModel.from_pretrained(base, "musapeker/pix2db-2b", subfolder="adapter")
```

## Repository contents

| Path | What |
|---|---|
| `model.safetensors`, configs | merged model (v2) |
| `adapter/` | LoRA adapter (r=64) the model was merged from |
| `eval_runs_v2/` | raw outputs and scores of every system on every eval set (v2) |
| `eval_runs/` | the same for the earlier synthetic-only v1 |
| tag `v1` | the v1 weights |

## Results

| System | Synthetic test<br>table exact | FK recall | PubTabNet F1 | FinTabNet F1 | CORD recall | Synth. receipts recall | TabRecSet (unseen) F1 |
|---|---|---|---|---|---|---|---|
| **pix2db-2b** | **0.86** | **0.99** | **0.81** | **0.96** | **0.93** | **1.00** | 0.52 |
| Qwen3-VL-8B → SQL | 0.75 | 0.75 | 0.52 | 0.59 | 0.76 | 0.87 | 0.45 |
| Qwen3-VL-8B → HTML → pandas | 0.47 | 0.00 | 0.78 | 0.87 | 0.44 | 0.38 | **0.58** |
| Qwen3-VL-4B → SQL | 0.66 | 0.25 | 0.48 | 0.48 | 0.79 | 0.77 | 0.38 |
| Qwen3-VL-2B → SQL (base) | 0.53 | 0.23 | 0.30 | 0.36 | 0.59 | 0.67 | 0.31 |

All SQL systems go through the same repair layer. PubTabNet/FinTabNet/CORD numbers are on held-out splits of
datasets whose train splits were used for training; TabRecSet was never used for training (see the GitHub
README for the header-row caveat on that set). Evaluation outputs: `eval_runs_v2/` in this repo.

## Training

Qwen3-VL-2B-Instruct + LoRA (r=64, α=128, language model only, vision tower frozen), merged.
1 epoch over ~36.6k examples ([pix2db-data](https://huggingface.co/datasets/musapeker/pix2db-data)):
14k synthetic Spider renders (6 difficulty levels incl. documents with foreign keys, scans, charts),
3k synthetic receipts, 10k PubTabNet, 8k FinTabNet, 795 CORD receipts (×2). lr 1e-4 cosine, effective batch 16,
~6 h on one A40. The previous synthetic-only version is tagged `v1`.

## Limitations

No handwriting; long tables (> ~30 rows) and dense financial statements are under-represented; charts without
value labels are approximate; table/column names are chosen by the model.

## License

Apache-2.0. Training data derived from Spider (CC BY-SA 4.0), PubTabNet & FinTabNet (CDLA-Permissive-1.0),
CORD (CC BY 4.0).
