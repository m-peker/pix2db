#!/bin/bash
# Merge the trained adapter, run all systems on all eval sets with vLLM, score everything.
# Usage: bash scripts/eval_all.sh CKPT_DIR TAG
set -e
CKPT=${1:-/workspace/ckpt/qwen3vl2b-lora-v1/final}
TAG=${2:-pix2db-2b-v1}
BASE=Qwen/Qwen3-VL-2B-Instruct
cd /workspace/pix2db
. /workspace/env.sh
[ -d /workspace/models/$TAG ] || python scripts/merge_lora.py --base $BASE --adapter $CKPT --out /workspace/models/$TAG
SETS="data/test data/real_pubtabnet data/real_cord"
V=/workspace/vllm-venv/bin/python
export PATH=/workspace/vllm-venv/bin:$PATH  # vLLM compile needs ninja on PATH
export HF_HOME=/workspace/.cache/huggingface
$V scripts/infer_vllm.py --data $SETS --model /workspace/models/$TAG --tag $TAG --prompt sql --out runs/eval
for m in Qwen/Qwen3-VL-2B-Instruct Qwen/Qwen3-VL-4B-Instruct Qwen/Qwen3-VL-8B-Instruct; do
  $V scripts/infer_vllm.py --data $SETS --model $m --prompt sql --out runs/eval
done
$V scripts/infer_vllm.py --data $SETS --model Qwen/Qwen3-VL-8B-Instruct --prompt html --out runs/eval
for s in test real_pubtabnet real_cord; do
  python scripts/score.py --data data/$s --runs runs/eval/$s --repair > runs/eval/$s/report.txt 2>&1
done
echo EVALDONE
