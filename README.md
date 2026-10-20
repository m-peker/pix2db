# pix2db

**Image → working SQLite database.** Give it a screenshot or photo of a table, form, invoice, receipt
or chart; get back `CREATE TABLE` + `INSERT` statements that actually run — with types, primary keys,
foreign keys between related tables, and a verify/repair layer that tells you when something looks off.

```python
from pix2db import Pix2DB

model = Pix2DB.from_pretrained("musapeker/pix2db-2b")
db = model.extract("invoice.png")

print(db.sql)                      # the schema + rows
db.tables                          # {"invoice": DataFrame, "line_items": DataFrame}
db.query("SELECT SUM(price) FROM line_items")
db.save("invoice.sqlite")
db.warnings                        # e.g. "line_items.qty: 1 non-numeric value(s) in a INTEGER column"
```

## Why

OCR → text → LLM pipelines lose table structure, and VLMs that output HTML/Markdown still leave you
with a layout, not a database. Real documents have merged cells, multi-level headers, a header block
plus line items, totals rows, thousand separators and currency signs. pix2db is trained to turn the
*layout* into a *relational schema*:

| In the image | In the database |
|---|---|
| merged cell spanning 3 rows | value repeated in each of the 3 rows |
| two-level header ("Figures → Age") | single column `age` |
| `$1,250.00`, `5 Mar 2009` | `1250.0` (REAL), `'2009-03-05'` |
| invoice header + item table | two tables + `FOREIGN KEY` |
| "Total" row | not stored (derived) |
| bar / line / pie chart | category column + one column per series |

## Results

_Filled in after training — see `results/`._

## Verify / repair layer

Every model output goes through deterministic checks before you see it: unescaped quotes, SQL keywords
used as column names, duplicate primary keys and truncated output are repaired statement by statement;
empty tables, values that contradict their declared type, duplicate rows and broken foreign keys are
reported as warnings.

## Training data

Synthetic, with a free and exact gold database: tables sampled from the 146 training databases of
[Spider](https://yale-lily.github.io/spider) (CC BY-SA 4.0), rendered with HTML/CSS and matplotlib at six
difficulty levels (clean, styled, hierarchical, documents with foreign keys, scanned/photographed,
charts). Evaluation uses Spider databases never seen in training plus real images
(PubTabNet tables, CORD receipts).

## Reproduce

```bash
pip install -e ".[train]" && playwright install chromium
python scripts/make_set.py --spider SPIDER/database --dbs data/splits/train_dbs.txt --out data/train \
    --counts 1:2000,2:3500,3:5500,4:5000,5:5000,6:3000
python scripts/train.py --config configs/train_2b.yaml
python scripts/infer.py --data data/test --model Qwen/Qwen3-VL-2B-Instruct --adapter CKPT/final --out runs/test
python scripts/score.py --data data/test --runs runs/test --repair
```

## License

Code and model: Apache-2.0 (base model Qwen3-VL-2B-Instruct is Apache-2.0).
Training data derived from Spider (CC BY-SA 4.0).

## Related work

OptiSQL (arXiv 2601.13695) generates a SQL *query* from a table image; MTabVQA (arXiv 2506.11684) does
visual QA over rendered tables. pix2db instead reconstructs the *database itself* — once — so any
number of queries run deterministically on real SQLite.
