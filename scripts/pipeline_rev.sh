#!/bin/bash
# Revision experiments, fully detached: baselines on new sets -> 5 trainings (merge, eval, upload after each)
# -> scoring -> upload -> stop pod. Docling runs on CPU in parallel.
. /workspace/env.sh; cd /workspace/pix2db
export PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
L=/workspace/logs; R=runs/rev; REPO=musapeker/pix2db-revision
V=/workspace/vllm-venv/bin/python
MAIN="data/test data/real_pubtabnet data/real_cord data/real_fintabnet data/test_receipt data/unseen_tabrecset"
NEW="data/real_invoices data/test_chart"
DEG=$(ls -d data/degrade/*)
log() { echo "[$(date '+%F %T')] $*" | tee -a $L/pipeline_rev.log; }
upload() { hf upload $REPO "$1" "$2" --private --quiet >> $L/upload.log 2>&1 || log "upload failed: $1"; }
infer() {  # model tag prompt sets...
  local m=$1 t=$2 p=$3; shift 3
  PATH=/workspace/vllm-venv/bin:$PATH $V scripts/infer_vllm.py --data $@ --model $m --tag $t --prompt $p --out $R \
    >> $L/infer_$t.log 2>&1 || log "infer failed: $t"
}

log "start"

# 1. existing models on the new sets (main sets were scored in v2)
hf download musapeker/pix2db-2b --exclude "eval_runs/*" --exclude "adapter/*" --local-dir /workspace/models/pix2db-2b-v2 > /dev/null
infer /workspace/models/pix2db-2b-v2 pix2db-2b-v2 sql $NEW
for m in Qwen/Qwen3-VL-2B-Instruct Qwen/Qwen3-VL-4B-Instruct Qwen/Qwen3-VL-8B-Instruct; do
  infer $m $(basename $m) sql $NEW
done
infer Qwen/Qwen3-VL-8B-Instruct Qwen3-VL-8B-Instruct html $NEW
R=runs/rev/degrade
infer /workspace/models/pix2db-2b-v2 pix2db-2b-v2 sql $DEG
infer Qwen/Qwen3-VL-8B-Instruct Qwen3-VL-8B-Instruct sql $DEG
infer Qwen/Qwen3-VL-8B-Instruct Qwen3-VL-8B-Instruct html $DEG
R=runs/rev
upload runs/rev runs/rev
log "baselines done"

# Docling (TableFormer + EasyOCR) on the GPU next to training: 2 shards, small memory footprint
for k in 0 1; do
  ( P=/workspace/docling-venv/bin/python
    $P scripts/run_docling.py --data $MAIN $NEW --out runs/rev --device cuda --threads 2 --shard $k --num-shards 2
    $P scripts/run_docling.py --data $DEG --out runs/rev/degrade --device cuda --threads 2 --shard $k --num-shards 2
  ) > $L/docling_gpu_$k.log 2>&1 &
done

# 2. trainings, most informative first
for name in html synth seed1 seed2 real; do
  cfg=configs/train_2b_$name.yaml; out=/workspace/ckpt/rev_$name
  if [ ! -f $out/final/adapter_model.safetensors ]; then
    log "train $name"
    python scripts/train.py --config $cfg > $L/train_$name.log 2>&1
    grep -q Traceback $L/train_$name.log && log "train $name FAILED" && continue
  fi
  upload $out/final adapters/rev_$name
  upload $L/train_$name.log logs/train_$name.log
  [ -d /workspace/models/rev_$name ] || python scripts/merge_lora.py --base Qwen/Qwen3-VL-2B-Instruct \
      --adapter $out/final --out /workspace/models/rev_$name >> $L/merge.log 2>&1
  p=sql; [ $name = html ] && p=html
  infer /workspace/models/rev_$name rev_$name $p $MAIN $NEW
  R=runs/rev/degrade; infer /workspace/models/rev_$name rev_$name $p $DEG; R=runs/rev
  upload runs/rev runs/rev
  rm -rf $out/checkpoint-*
  log "done $name"
done

# 3. merge docling shards, score everything (CPU)
wait
for d in runs/rev/*/ runs/rev/degrade/*/; do
  ls $d/docling.part* > /dev/null 2>&1 || continue
  cat $d/docling.part* >> $d/docling__html.jsonl && rm $d/docling.part*
done
log "docling merged"
for d in $(ls -d runs/rev/*/ runs/rev/degrade/*/ | grep -v '/degrade/$'); do
  s=$(basename $d); data=data/$s; [ -d data/degrade/$s ] && [[ $d == *degrade* ]] && data=data/degrade/$s
  python scripts/score.py --data $data --runs $d --repair > $d/report.txt 2>&1
done
upload runs/rev runs/rev
upload $L logs
log "ALL_DONE"

# 4. stop the pod (API key is in the container environment)
export $(tr '\0' '\n' < /proc/1/environ | grep '^RUNPOD_' | xargs)
runpodctl config --apiKey "$RUNPOD_API_KEY" > /dev/null 2>&1
runpodctl stop pod "$RUNPOD_POD_ID" >> $L/pipeline_rev.log 2>&1
