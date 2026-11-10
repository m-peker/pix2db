# FAITH revision — experiment notes (2026-11-09)

Pod: A40, **9 vCPU, 50 GB RAM** (RUNPOD_CPU_COUNT=9) — do not run many CPU processes.
Pipeline: `scripts/pipeline_rev2.sh` on pod (log `/workspace/logs/pipeline_rev.log`), uploads to HF
`musapeker/pix2db-revision` (private), stops the pod at the end. Local snapshot: `paper/cache/rev/` (data metas + runs).

## New evaluation sets
- `real_invoices`: 490 invoices (katanaml-org/invoices-donut-data-v1, MIT; train+val+test, never used for training).
  Gold = invoice(PK) + item(FK). Annotation omits "No.", "UM" columns and the summary table → scored by **recall**.
- `test_chart`: 300 charts from test DBs with chart_kind/value_labels (bar 98, barh 76, line 67, pie 59; labeled 198).
- `degrade/<variant>`: the 150 L5 test scenes re-rendered clean (level 4 layout) + one degradation each at the strongest
  scan_augment setting: rotation 2.5°, lighting, noise σ=9, blur 0.9, contrast 0.8, grayscale, JPEG q45, all (scan_augment).
- Docling (TableFormer ACCURATE + EasyOCR full-page, cell matching; retry on a padded page if no table found).
  Upscaling 2x/3x does not help (PubTabNet 20 imgs: .17/.20/.18).

## Results so far
Invoices (recall / FK recall / tables per output):
v2 .541 / .01 / 1.0 · 8B-SQL .864 / .97 / 3.1 · 4B .795 / .93 · 2B .427 / 0 · 8B-HTML .115 · Docling .097
→ our model transcribes only the item table of a full-page invoice (reads items perfectly); FK skill does not transfer.

Charts (exact): v2 .713, 8B .747, 4B .670, 8B-HTML .633, 2B .380, Docling 0.
  by kind (v2/8B): bar .61/.72, barh .78/.78, line .67/.73, pie .85/.76; unlabeled vs labeled (v2) .69/.73, F1 .946/.938.

Degradation (exact; clean → rotation, lighting, noise, blur, contrast, gray, jpeg, all):
v2   .917 → .907 .877 .893 .893 .910 .893 .897 .900
8B   .660 → .653 .667 .643 .637 .667 .653 .693 .647
8B-HTML .203 → ~.17–.25 ; Docling F1 .61 → blur .24, rotation .54
→ VLMs barely affected by these degradations (synthetic L5 is mild); Docling is sensitive to blur/rotation.

Docling per set (F1 unless noted): synth exact .096 (L1 .21 … L5 .02), PubTabNet .152, FinTabNet .696,
CORD recall .043 (77% no table), receipts recall .114, TabRecSet .201, invoices recall .097.

Repair ablation (pooled, 5 sets; exec / F1), from `paper/analyze_repair.py`:
v2: none .970/.938 → full .991/.952; row_fallback alone .990/.949; drop_pk alone .983/.949.
v1: none .824/.716 → full .948/.764. 2B: .782/.607 → .868/.639. 8B: .959/.801 → .997/.810.
Info loss (full repair, v2): 29 rescued outputs (F1 .77), 7 rows dropped of 10,234 gold rows, 18 PKs dropped.
2B base: salvage slightly lowers F1 (-salvage .643 vs full .639).

Schema metrics, synthetic test (v2 vs 8B-SQL): FK precision 209/212 vs 169/211; PK precision 537/574 vs 512/909;
ref. integrity .976 vs .933; table count ok 1.00 vs .98; column count ok .96 vs .94; FK column-level recall .97 vs .75.
Query equivalence (first 200 test items): v2 .932, 8B-SQL .946, 8B-HTML .693 → compute on full sets.

## Pending (training on pod): html-target, synth-only 36,589, seed1, seed2, real-only 19,589.

Query-execution equivalence (pooled share of auto-generated aggregate queries with equal results; +repair):
set:        synth  PTN   FTN   CORD  rcpt  TabRec  inv   chart
v2          .976  .800  .916  .936  .996  .570   .468  .937
v1          .987  .402  .318  .363  .192  .434   –     –
8B-SQL      .968  .614  .423  .732  .754  .493   .884  .950
8B-HTML     .689  .729  .427  .223  .098  .602   .091  .836
4B          .944  .537  .353  .768  .701  .418   .820  .936
2B          .829  .370  .267  .558  .566  .362   .416  .679
Docling     .387  .099  .220  .027  .033  .126   .088  0
All scores in paper/cache/rev/runs/rev/<set>/scores.csv (v2-era outputs copied in).

## Task-adapted baseline: same 2B, same v2 mixture, trained to emit HTML (rev_html, done 2026-11-09 21:16)
Scores in `paper/cache/rev/runs/rev/<set>/scores_rev_html.csv`. HTML-2B vs SQL-v2(+repair):
set:          F1 HTML / v2     exact HTML / v2   q-equiv HTML / v2
synth         .974 / .969      .854 / .856       .985 / .976
PubTabNet     .807 / .805      .287 / .293       .799 / .800
FinTabNet     .954 / .964      .767 / .753       .918 / .916
CORD          .932 / .922      .617 / .633       .951 / .936
receipts      .998 / .998      .933 / .953       .996 / .996
TabRecSet     .531 / .525      .087 / .080       .549 / .570
invoices(rec) .547 / .541      –                 .569 / .468
chart         .944 / .941      .707 / .713       .936 / .937
degrade all   .987 / .980      .917 / .920       .992 / .985
FK recall (synthetic L4): HTML 0 (format cannot express keys) vs v2 .99. Type acc .989 vs .992.
→ Cell content is equal when the 2B model is fine-tuned for HTML: the gain over 8B→HTML comes from
  fine-tuning, not from the SQL target. What SQL adds: keys/FKs, types and one-pass DB (no converter).
  Must be stated plainly in the paper (Reviewer B: task-adapted baselines).

## Seed 1 (same v2 mixture/config, seed 1) — scores_rev_seed1.csv
F1 / exact (seed42 → seed1, +repair): synth .969/.856 → .972/.854 (FK .986 → .995); PTN .805/.293 → .788/.273;
FTN .964/.753 → .963/.773; CORD .922/.633 → .923/.650; receipts .998/.953 → .994/.940; TabRec .525/.080 → .530/.080;
invoices F1 .572 → .596 (FK 0); chart .941/.713 → .941/.703. Seed variation ≈ ±.01–.02 F1.

## Pod incidents (2026-11-10)
- synth run: one corrupt PNG in data/train (train_s028_L4_00019) → fixed from HF, retried by after_rev.sh.
- seed2 run: disk full (100 GB) at checkpoint-1200 → freed 41 GB (8B/4B weights, HF dataset cache, merged models);
  retried by `scripts/after_rev.sh seed2 synth` (resumes from checkpoint-900) after the main pipeline.
  `runpodctl` wrapper in /workspace/venv/bin defers the main pipeline's stop until after_rev.sh finishes.
