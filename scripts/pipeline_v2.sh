#!/bin/bash
# Unattended: train v2 -> eval -> upload (private) -> verify -> stop pod. Leaves the pod running on failure.
LOG=/workspace/logs/pipeline_v2.log
exec >> $LOG 2>&1
. /workspace/env.sh; cd /workspace/pix2db
echo "[$(date)] train"
PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python scripts/train.py --config configs/train_2b_v2.yaml \
  > /workspace/logs/train_2b_v2.log 2>&1 || { echo "TRAIN FAILED"; exit 1; }
grep -q "saved /workspace/ckpt" /workspace/logs/train_2b_v2.log || { echo "TRAIN DID NOT SAVE"; exit 1; }
echo "[$(date)] eval"
bash scripts/eval_v2.sh > /workspace/logs/eval_v2.log 2>&1 || { echo "EVAL FAILED"; exit 1; }
echo "[$(date)] upload"
python - <<PY || { echo "UPLOAD FAILED"; exit 1; }
from huggingface_hub import HfApi
api = HfApi()
api.create_tag("musapeker/pix2db-2b", tag="v1", exist_ok=True)
# the LoRA adapter lives in the model repo under adapter/
api.upload_folder(folder_path="/workspace/ckpt/qwen3vl2b-lora-v2/final", repo_id="musapeker/pix2db-2b", path_in_repo="adapter", allow_patterns=["adapter_config.json", "adapter_model.safetensors"])
api.upload_folder(folder_path="/workspace/models/pix2db-2b-v2", repo_id="musapeker/pix2db-2b",
                  commit_message="v2 merged model (synthetic + PubTabNet + FinTabNet + receipts)")
api.upload_folder(folder_path="/workspace/pix2db/runs/eval", repo_id="musapeker/pix2db-2b", path_in_repo="eval_runs_v2",
                  commit_message="v2 eval outputs and reports")
api.upload_file(path_or_fileobj="/workspace/logs/train_2b_v2.log", path_in_repo="eval_runs_v2/train_2b_v2.log",
                repo_id="musapeker/pix2db-2b")
files = {f.rfilename: f.size for f in api.model_info("musapeker/pix2db-2b", files_metadata=True).siblings}
assert files.get("model.safetensors", 0) > 1e9 and any(k.startswith("eval_runs_v2/") and k.endswith("report.txt") for k in files)
print("verified")
PY
echo "[$(date)] uploads verified, stopping pod"
runpodctl stop pod "$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_POD_ID=//p')" || echo "STOP FAILED"
