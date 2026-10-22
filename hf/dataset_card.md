---
license: other
license_name: mixed
license_link: https://github.com/m-peker/pix2db#license
task_categories:
  - image-text-to-text
  - table-question-answering
language:
  - en
tags:
  - table-extraction
  - text-to-sql
  - sqlite
  - receipts
  - charts
size_categories:
  - 10K<n<100K
---

# pix2db-data

Images of tables, forms, invoices, receipts and charts paired with a **gold SQLite database** (`sql` column:
`CREATE TABLE` + `INSERT`, ready to run). Used to train and evaluate
[pix2db-2b](https://huggingface.co/musapeker/pix2db-2b). Code: https://github.com/m-peker/pix2db

Each row: `image`, `id`, `level`, `level_name`, `kind`, `source_db`, `sql` (gold dump), `scene` (gold as JSON),
`num_tol_abs` (numeric tolerance, charts without value labels), `recall_only` (score with recall).

## Splits

| Split | Rows | What | License of the source |
|---|---|---|---|
| `train` | 24,000 | synthetic renders of 146 Spider training DBs, levels 1–6 | CC BY-SA 4.0 (Spider) |
| `validation` | 600 | synthetic, 20 Spider dev DBs | CC BY-SA 4.0 |
| `test` | 900 | synthetic, 40 Spider test-only DBs (never in train) | CC BY-SA 4.0 |
| `train_real` | 18,794 | real tables: PubTabNet train (9,999), FinTabNet train (8,000); real receipts: CORD train (795) | CDLA-Permissive-1.0 / CC BY 4.0 |
| `train_receipt` | 3,000 | synthetic receipts | CC BY 4.0 (this work) |
| `real_pubtabnet` | 150 | PubTabNet validation tables | CDLA-Permissive-1.0 |
| `real_fintabnet` | 150 | FinTabNet validation tables | CDLA-Permissive-1.0 |
| `real_cord` | 60 | CORD test receipts (`recall_only`) | CC BY 4.0 |
| `test_receipt` | 150 | synthetic receipts | CC BY 4.0 |
| `unseen_tabrecset` | 150 | TabRecSet English tables, cropped (never in train) | CC BY 4.0 |

Synthetic levels: 1 clean · 2 styled (fonts, colors, separators, currency, dates) · 3 hierarchical (merged
cells, two-level headers, transposed, totals rows) · 4 document (key-value header + item table, gold has a
FOREIGN KEY) · 5 scanned/photographed · 6 chart (bar/line/pie) · 9 receipt.

## Conventions of the gold database

Merged cells repeated in every covered row; multi-level headers joined into one snake_case name; numbers without
separators/currency, accounting `(1,234)` → `-1234`, lone dashes → NULL; totals rows not stored; identifiers quoted
only when needed. Real tables (PubTabNet/FinTabNet/TabRecSet) are converted from their HTML/cell annotations;
tables with body colspans (section rows) are excluded because they have no unambiguous relational form.

## Attribution

Spider (Yu et al., 2018), PubTabNet (Zhong et al., 2020), FinTabNet (Zheng et al., 2021), CORD (Park et al.,
2019), TabRecSet (Yang et al., Scientific Data 2023). Please cite the original datasets when using these splits.
