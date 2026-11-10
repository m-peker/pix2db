#!/bin/bash
# Revision data: restore v2 splits, extra synthetic (synthetic-only control), chart test, invoices, degradations.
. /workspace/env.sh; cd /workspace/pix2db
L=/workspace/logs
SP="/workspace/data/raw/spider/spider_data/database /workspace/data/raw/spider/spider_data/test_database"
python scripts/pull_data.py --out data > $L/rev_pull.log 2>&1
mkdir -p data/splits
python - <<'PY'
import json
from pathlib import Path
S = Path("/workspace/data/raw/spider/spider_data")
ids = lambda *fs: {d["db_id"] for f in fs for d in json.load(open(S / f))}
train = ids("train_spider.json", "train_others.json"); dev = ids("dev.json"); test = ids("test.json") - train - dev
used = {json.loads(l)["scene"]["db_id"] for l in open("data/train/meta.jsonl")}
print("train dbs", len(train), "used in v1 train", len(used), "outside", len(used - train), "test-only", len(test))
Path("data/splits/train_dbs.txt").write_text(chr(10).join(sorted(train)))
Path("data/splits/test_dbs.txt").write_text(chr(10).join(sorted(test)))
PY
for i in $(seq 0 23); do
  python scripts/make_set.py --spider $SP --dbs data/splits/train_dbs.txt --out data/synth_extra \
    --counts 1:799,2:1398,3:2198,4:1998,5:1998,6:1198 --shard $i --num-shards 24 --seed 101 --prefix sx_ \
    > $L/rev_sx_$i.log 2>&1 &
done
for i in 0 1 2 3; do
  python scripts/make_set.py --spider $SP --dbs data/splits/test_dbs.txt --out data/test_chart --counts 6:300 \
    --shard $i --num-shards 4 --seed 11 --prefix ctest_ > $L/rev_chart_$i.log 2>&1 &
done
python scripts/make_invoices.py --out data/real_invoices > $L/rev_inv.log 2>&1 &
python scripts/make_degrade.py --src data/test --out data/degrade > $L/rev_deg.log 2>&1 &
wait
python scripts/check_gold.py synth_extra test_chart real_invoices degrade/clean > $L/rev_check.log 2>&1
echo DATA_REV_DONE
