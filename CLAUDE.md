# Project: pix2db — image → working SQLite database

> Project memory for Claude Code. Read at the start of every session.
> Communication in Turkish; code, identifiers and commit messages in English.
> Note: `Desktop/CLAUDE.md` belongs to a different project (GATE-QE). It does not apply here.

## Goal

A small VLM (2–4B) that takes an image of a table, form, invoice, dashboard or chart and outputs a
**working SQLite database dump** (`CREATE TABLE` + `INSERT`), with:
1. Layout → relational schema: merged cells expanded, multi-level headers flattened, types inferred,
   units/currency/thousand separators stripped, dates normalized.
2. Multiple related tables from one image (e.g. invoice header + line items) with foreign keys.
3. Self-verification: the dump is checked (executes, totals match, types valid) and flagged/retried.
4. Charts → typed tables (approximate values, tolerance-based scoring).

Deliverables: Hugging Face model + Gradio Space + pip package + GitHub repo (github.com/m-peker).
HF user: `musapeker`. A paper is optional, later.

## Positioning vs prior work (checked 2026-10-20)

- **OptiSQL** (arXiv 2601.13695, Jan 2026): image + question → SQL query, single table, clean renders
  of Spider 2.0-Snow. Does NOT build a database, no merged cells/forms/scans/charts, no HF model.
- **MTabVQA** (arXiv 2506.11684): multi-table visual QA from rendered Spider/BIRD tables. QA, not SQL.
- Table recognition (image → HTML): Qwen2.5-VL, docling, olmOCR, GOT-OCR2, TABLET, PubTables-v2.
- Chart → table: DePlot, MatCha, UniChart, ChartGemma.
- The key baseline to beat: **strong VLM → HTML → 20-line script → SQLite.** If we cannot beat it on
  hierarchical/document levels, the project pivots to "benchmark + verification layer".

## Infrastructure

- Local PC: code editing only. No heavy compute locally.
- RunPod: `ssh runpod` (alias in ~/.ssh/config). A40 46 GB. **No persistent volume**: anything not
  pushed to GitHub / HF Hub is lost when the pod is deleted.
- On pod: `. /workspace/env.sh` (sets `HF_HOME=/workspace/.cache/huggingface`, venv on PATH).
  Venv: `/workspace/venv` (system torch 2.8 + transformers 5.x).
- Long jobs: start with `setsid nohup bash -c "..." > log 2>&1 < /dev/null & disown` (fully detached).
  Training: `PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- 2B training with per-device batch 8 OOMs at step 71 (full-vocab logits of a long batch, 12.6 GB):
  use batch 4 × accum 4. Always check the log tail for Traceback, not just the process list.
- vLLM lives in a separate venv `/workspace/vllm-venv` (own torch); use it only for inference
  (`scripts/infer_vllm.py`, needs merged models: `scripts/merge_lora.py`).
- Splits: Spider train DBs → data/train (24k); dev DBs → data/val (600); test-only DBs → data/test (900).
  Real eval: data/real_pubtabnet (150 tables), data/real_cord (60 receipts, recall_only).
- Raw data on pod: `/workspace/data/raw/spider/spider_data/{database,test_database}` (Spider 1.0, CC-BY-SA).
- Never ask the user to paste tokens into chat. HF token can be copied from the local machine to the pod over SSH.
- Pod SSH sessions drop ("Connection reset by peer"): never run long work inside an SSH session. Put the whole
  remaining plan in one detached chain script on the pod (wait for data -> check -> train -> eval -> upload -> stop),
  because a local waiter dies with the Claude session (this left the v2 pod idle for hours).
- Pod setup: `bash scripts/setup_pod.sh`; restore v1 data: `python scripts/pull_data.py`.

## Data generation (synthetic, gold DB is free)

Source: Spider SQLite databases. A "scene" = 1 table (or parent+child via FK) with sampled rows/cols.
Difficulty levels:
- L1 clean HTML table
- L2 styled (fonts, colors, zebra, humanized headers, thousand separators, currency, date formats)
- L3 hierarchical (rowspan merged cells on a grouping column, multi-level headers)
- L4 document (master-detail: parent as key-value form, child as item table; gold = 2 tables + FK)
- L5 scan (L3/L4 + rotation, blur, noise, JPEG, uneven lighting)
- Charts (later): ChartQA / PlotQA gold tables.

## Evaluation (name-agnostic)

Predicted DB vs gold DB: table matching + column alignment by value overlap (Hungarian) + row matching.
Metrics: parse/exec rate, cell F1, table exact match, type accuracy, FK recovery. Later: downstream
QA accuracy (text-to-SQL on predicted DB vs gold SQL on gold DB).

## Rules

- Smoke test every new script on ~10 items and show output before full runs.
- Seed 42 everywhere; configs in YAML; cache all model outputs (resumable).
- Estimate GPU time before each GPU stage and tell the user.
- Update `docs/progress.md` at the end of each session.

## Phases

- [x] P0 idea, positioning, prior-work check, pod setup
- [x] P1 feasibility: 150 images (5 levels), zero-shot Qwen3-VL 2B/4B/8B + Qwen2.5-VL-3B — see docs/progress.md
- Base model: Qwen3-VL (Apache-2.0). Qwen2.5-VL-3B is non-commercial licence — do not ship on it.
- [x] P2 go
- [x] v1 trained/evaluated (results/v1): synthetic exact .85 (8B: .75) but weak on real images
- [ ] v2: + real PubTabNet/FinTabNet/CORD train data + synthetic receipts (scripts/pipeline_v2.sh)
- [ ] P3 full data generation (+ charts, + real scans eval set)
- [ ] P4 fine-tune (LoRA) 2–4B model
- [ ] P5 verification layer, packaging, HF model card, Space, GitHub release
