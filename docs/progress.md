# Progress

## 2026-10-20 — Session 1

### Done
- Idea narrowed to **pix2db**: image → working SQLite DB (schema, types, FKs, self-check).
- Prior-work check: OptiSQL (2601.13695) = image+question → SQL query, single clean table, no model on HF.
  MTabVQA (2506.11684) = visual QA on rendered Spider/BIRD tables. Our gap: building the DB itself,
  hierarchical layouts, documents with FKs, scans, charts, verification.
- Licence: Qwen2.5-VL-3B is Qwen Research licence (non-commercial). **Qwen3-VL-2B/4B/8B are Apache-2.0** → base model.
- RunPod A40 set up (`ssh runpod`, `/workspace/venv`, `/workspace/env.sh`). No persistent volume.
- Spider 1.0 DBs downloaded to pod (HAL-9001/spider-databases, 744 sqlite).
- Code: scene sampling, HTML/CSS renderer (L1–L5), safe SQL loader, HTML→pandas baseline, name-agnostic metrics.
- Feasibility set: 150 images (30 per level), seed 42. Zero-shot results in `results/feasibility/`.

### Feasibility results (zero-shot, table exact match)

| system | L1 | L2 | L3 | L4 | L5 | all | FK recall |
|---|---|---|---|---|---|---|---|
| Qwen3-VL-8B → HTML → script | .90 | .87 | .13 | .17 | .25 | .46 | 0 |
| Qwen3-VL-8B → SQL | .77 | .67 | .47 | .73 | .42 | .61 | .69 |
| Qwen3-VL-4B → SQL | .53 | .57 | .47 | .62 | .55 | .55 | .44 |
| Qwen3-VL-2B → SQL | .77 | .47 | .40 | .63 | .42 | .54 | .31 |
| Qwen2.5-VL-3B → SQL | .33 | .27 | .13 | .42 | .25 | .28 | .54 |

Findings:
1. HTML→script pipeline is strong on flat tables (L1–L2) but collapses on hierarchical/doc/scan (L3–L5).
2. Direct SQL zero-shot is weak everywhere (best .61): models read the content but fail on SQL
   validity (unescaped quotes, reserved words, wrong PRIMARY KEY → UNIQUE violations), invent tables,
   omit FOREIGN KEY constraints. These are exactly what fine-tuning + a verify/repair loop fix.
3. → GO for fine-tuning. Caveat: synthetic closed loop; we must add a real-image eval set.

### Next
- P3 data v2: ~20–30k training images (Spider train DBs only; Spider test DBs held out for eval),
  harder variants (longer tables, wide tables, totals rows, multi-table pages, charts from ChartQA/PlotQA),
  plus real-image eval (FinTabNet / PubTabNet / real invoices).
- P4 LoRA fine-tune Qwen3-VL-2B and 4B.
- Verification/repair loop (exec check, quote escaping, PK sanity, totals check).

### Open questions
- Project name final? (`pix2db` placeholder)
- When to create the GitHub repo (private first?).

## 2026-10-21 — Session 1 (night)

### Done
- Data v2: 24k train / 600 val / 900 test (disjoint Spider DBs), 6 levels incl. charts; real eval sets
  real_pubtabnet (150) and real_cord (60). Pushed to HF `musapeker/pix2db-data` (private, parquet).
- Training: Qwen3-VL-2B LoRA r64, 1 epoch, bs 4 × accum 4 (bs 8 OOMed at step 71). 2h33m on A40.
  Adapter: HF `musapeker/pix2db-2b-lora` (private).
- Eval with vLLM (0.09 s/image): ours + Qwen3-VL 2B/4B/8B (sql) + 8B (html) on test, real_pubtabnet, real_cord.
- Pod runs `scripts/finish_and_stop.sh` unattended: score → upload merged model + eval_runs to HF
  `musapeker/pix2db-2b` (private) → verify → `runpodctl stop pod`. Log: /workspace/logs/finish.log.

### Preliminary results (ours, before final scoring with NFKC metric)
- Synthetic test: cell F1 .96 (.97 with repair), table exact .84 (.85), FK recall .99. Charts weakest (exact .59).
- Real PubTabNet: F1 only ~.27 — mostly metric/gold artefacts (en-dash vs hyphen, superscripts) and free-text
  headers ('# of sequences¹') breaking CREATE TABLE → fixed in metric (NFKC) and repair (sanitize identifiers).
- Real CORD receipts: recall ~.44–.49. Real domain gap: no receipt-like layouts in training data.

### Next (v2 data)
- Receipt / invoice templates (unit price, qty, line total, free-text lines between items).
- Headers with symbols, units, footnote markers (gold stays snake_case).
- Compare all systems once final reports are on HF (`eval_runs/*/report.txt`).
