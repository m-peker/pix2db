#!/bin/bash
# Evaluate v2 (+ v1 and zero-shot baselines) on all eval sets. Reuses v1 outputs from the Hub.
set -e
. /workspace/env.sh; cd /workspace/pix2db
CKPT=/workspace/ckpt/qwen3vl2b-lora-v2/final
[ -d /workspace/models/pix2db-2b-v2 ] || python scripts/merge_lora.py --base Qwen/Qwen3-VL-2B-Instruct --adapter $CKPT --out /workspace/models/pix2db-2b-v2
[ -d /workspace/models/pix2db-2b-v1 ] || hf download musapeker/pix2db-2b --exclude "eval_runs/*" --local-dir /workspace/models/pix2db-2b-v1 > /dev/null
if [ ! -d runs/eval ]; then
  hf download musapeker/pix2db-2b --include "eval_runs/*" --local-dir /tmp/v1runs > /dev/null
  mkdir -p runs && cp -r /tmp/v1runs/eval_runs runs/eval
  rm -f runs/eval/*/report.txt runs/eval/*/scores.csv runs/eval/train_2b.log
fi
SETS="data/test data/real_pubtabnet data/real_cord data/real_fintabnet data/test_receipt"
export PATH=/workspace/vllm-venv/bin:$PATH
V=/workspace/vllm-venv/bin/python
$V scripts/infer_vllm.py --data $SETS --model /workspace/models/pix2db-2b-v2 --tag pix2db-2b-v2 --prompt sql --out runs/eval
$V scripts/infer_vllm.py --data $SETS --model /workspace/models/pix2db-2b-v1 --tag pix2db-2b-v1 --prompt sql --out runs/eval
for m in Qwen/Qwen3-VL-2B-Instruct Qwen/Qwen3-VL-4B-Instruct Qwen/Qwen3-VL-8B-Instruct; do
  $V scripts/infer_vllm.py --data $SETS --model $m --prompt sql --out runs/eval
done
$V scripts/infer_vllm.py --data $SETS --model Qwen/Qwen3-VL-8B-Instruct --prompt html --out runs/eval
for s in test real_pubtabnet real_cord real_fintabnet test_receipt; do
  /workspace/venv/bin/python scripts/score.py --data data/$s --runs runs/eval/$s --repair > runs/eval/$s/report.txt 2>&1
done
echo EVAL_V2_DONE
