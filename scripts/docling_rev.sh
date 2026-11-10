#!/bin/bash
# Docling baseline on CPU, alongside training, sharded (EasyOCR on CPU is single-threaded in practice).
# Outputs: runs/rev[/degrade]/<set>/docling__html.jsonl (shards merged at the end)
. /workspace/env.sh; cd /workspace/pix2db
P=/workspace/docling-venv/bin/python
SETS="data/real_pubtabnet data/real_cord data/real_fintabnet data/test_receipt data/unseen_tabrecset data/real_invoices data/test_chart data/test"
N=40
for k in $(seq 0 $((N-1))); do
  ( OMP_NUM_THREADS=2 $P scripts/run_docling.py --data $SETS --out runs/rev --threads 2 --shard $k --num-shards $N
    OMP_NUM_THREADS=2 $P scripts/run_docling.py --data $(ls -d data/degrade/*) --out runs/rev/degrade --threads 2 \
      --shard $k --num-shards $N ) > /workspace/logs/docling_$k.log 2>&1 &
done
wait
for d in runs/rev/*/ runs/rev/degrade/*/; do
  ls $d/docling.part* > /dev/null 2>&1 || continue
  cat $d/docling.part* >> $d/docling__html.jsonl && rm $d/docling.part*
done
echo DOCLING_DONE > /workspace/logs/docling.done
