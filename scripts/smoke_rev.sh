#!/bin/bash
# Smoke tests for the revision pipeline (~10 items each). Outputs go to /workspace/smoke, never to runs/rev.
. /workspace/env.sh; cd /workspace/pix2db
export PYTHONUNBUFFERED=1
S=/workspace/smoke; mkdir -p $S
echo "== data counts"; for d in data/*/ data/degrade/*/; do echo "$d $(cat $d/meta*.jsonl 2>/dev/null | wc -l)"; done
echo "== html target example"
python -c "
import sys; sys.path.insert(0,'scripts'); sys.path.insert(0,'src')
from train import target_text; from pix2db.data import load_meta
it=[x for x in load_meta('data/real_train') if x['kind']=='pubtabnet'][0]; print(target_text(it,'html')[:400])
it=load_meta('data/real_invoices')[0]; from pix2db.scene import Scene; print(Scene.from_dict(it['scene']).to_sql()[:900])
import collections, json; print(collections.Counter((m['chart_kind'], m['value_labels']) for m in load_meta('data/test_chart')))"
for n in html synth; do
  sed "s#output_dir: .*#output_dir: $S/ckpt_$n#" configs/train_2b_$n.yaml > $S/cfg_$n.yaml
  python scripts/train.py --config $S/cfg_$n.yaml --max-steps 3 --limit 48 > $S/train_$n.log 2>&1
  echo "== train $n"; grep -E "source|train items|loss|Traceback|Error" $S/train_$n.log | tail -12
done
echo "== docling"
/workspace/docling-venv/bin/python scripts/run_docling.py --data data/real_invoices data/test --out $S/runs --limit 3 > $S/docling.log 2>&1
tail -3 $S/docling.log; head -c 600 $S/runs/real_invoices/docling__html.jsonl; echo
echo "== vllm on new sets (5 each)"
mkdir -p $S/sets; for d in real_invoices test_chart degrade/blur; do
  n=$(basename $d); mkdir -p $S/sets/$n; head -5 data/$d/meta.jsonl > $S/sets/$n/meta.jsonl; ln -sfn $PWD/data/$d/images $S/sets/$n/images
done
hf download musapeker/pix2db-2b --exclude "eval_runs/*" --exclude "adapter/*" --local-dir /workspace/models/pix2db-2b-v2 > /dev/null
PATH=/workspace/vllm-venv/bin:$PATH /workspace/vllm-venv/bin/python scripts/infer_vllm.py --data $S/sets/real_invoices $S/sets/test_chart $S/sets/blur \
  --model /workspace/models/pix2db-2b-v2 --tag pix2db-2b-v2 --prompt sql --out $S/runs > $S/infer.log 2>&1
tail -4 $S/infer.log
for n in real_invoices test_chart blur; do cp $S/runs/real_invoices/docling__html.jsonl /dev/null 2>&1
  python scripts/score.py --data $S/sets/$n --runs $S/runs/$n --repair 2>&1 | grep -A4 "== f1\|schema" | head -12; done
head -c 1200 $S/runs/real_invoices/pix2db-2b-v2__sql.jsonl
echo SMOKE_DONE
