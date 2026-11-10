#!/bin/bash
# Rerun trainings that failed in pipeline_rev2.sh (corrupt image, full disk), then stop the pod.
# Waits until the main pipeline asks to stop (runpodctl wrapper touches /workspace/stop_requested).
# Usage: setsid nohup bash scripts/after_rev.sh seed2 synth > /workspace/logs/after_rev.out 2>&1 < /dev/null &
. /workspace/env.sh; cd /workspace/pix2db
export PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
L=/workspace/logs; REPO=musapeker/pix2db-revision; V=/workspace/vllm-venv/bin/python
MAIN="data/test data/real_pubtabnet data/real_cord data/real_fintabnet data/test_receipt data/unseen_tabrecset"
NEW="data/real_invoices data/test_chart"; DEG=$(ls -d data/degrade/*)
log() { echo "[$(date '+%F %T')] $*" | tee -a $L/pipeline_rev.log; }
upload() { hf upload $REPO "$1" "$2" --private --quiet >> $L/upload.log 2>&1 || log "upload failed: $1"; }
infer() {  # model tag out sets...
  local m=$1 t=$2 out=$3; shift 3
  PATH=/workspace/vllm-venv/bin:$PATH $V scripts/infer_vllm.py --data $@ --model $m --tag $t --prompt sql --out $out \
    >> $L/infer_$t.log 2>&1 || log "infer failed: $t"
}

while [ ! -f /workspace/stop_requested ]; do sleep 120; done
for name in "$@"; do
  out=/workspace/ckpt/rev_$name
  log "train $name (retry)"
  [ -f $L/train_$name.log ] && mv $L/train_$name.log $L/train_${name}_fail$(date +%s).log
  python scripts/train.py --config configs/train_2b_$name.yaml > $L/train_$name.log 2>&1
  if grep -q Traceback $L/train_$name.log; then log "train $name FAILED again"; continue; fi
  upload $out/final adapters/rev_$name
  upload $L/train_$name.log logs/train_$name.log
  python scripts/merge_lora.py --base Qwen/Qwen3-VL-2B-Instruct --adapter $out/final \
    --out /workspace/models/rev_$name >> $L/merge.log 2>&1
  infer /workspace/models/rev_$name rev_$name runs/rev $MAIN $NEW
  infer /workspace/models/rev_$name rev_$name runs/rev/degrade $DEG
  upload runs/rev runs/rev
  upload $L logs
  rm -rf $out/checkpoint-* /workspace/models/rev_$name
  log "done $name"
done
log "ALL_DONE2"
touch /workspace/allow_stop
export $(tr '\0' '\n' < /proc/1/environ | grep '^RUNPOD_' | xargs)
/usr/bin/runpodctl config --apiKey "$RUNPOD_API_KEY" > /dev/null 2>&1
/usr/bin/runpodctl stop pod "$RUNPOD_POD_ID" >> $L/pipeline_rev.log 2>&1
