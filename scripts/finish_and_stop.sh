#!/bin/bash
# Runs unattended on the pod: wait for eval, upload merged model + results to HF (private),
# verify the uploads, then stop the pod. If any step fails, the pod is left running.
LOG=/workspace/logs/finish.log
exec >> $LOG 2>&1
. /workspace/env.sh
cd /workspace/pix2db
echo "[$(date)] waiting for eval"
until grep -qE "EVALDONE|Traceback" /workspace/logs/eval.log; do sleep 60; done
if ! grep -q EVALDONE /workspace/logs/eval.log; then echo "eval failed, leaving pod running"; exit 1; fi
python - <<PY || { echo "UPLOAD FAILED, leaving pod running"; exit 1; }
from huggingface_hub import HfApi
api = HfApi()
api.create_repo("musapeker/pix2db-2b", private=True, exist_ok=True)
api.upload_folder(folder_path="/workspace/models/pix2db-2b-v1", repo_id="musapeker/pix2db-2b",
                  commit_message="v1 merged model (Qwen3-VL-2B + LoRA, 24k synthetic, 1 epoch)")
api.upload_folder(folder_path="/workspace/pix2db/runs/eval", repo_id="musapeker/pix2db-2b",
                  path_in_repo="eval_runs", commit_message="v1 eval outputs and reports")
api.upload_file(path_or_fileobj="/workspace/logs/train_2b.log", path_in_repo="eval_runs/train_2b.log",
                repo_id="musapeker/pix2db-2b")
files = {f.rfilename: f.size for f in api.model_info("musapeker/pix2db-2b", files_metadata=True).siblings}
assert files.get("model.safetensors", 0) > 1e9, files
assert any(k.endswith("report.txt") for k in files), files
print("verified", len(files), "files")
PY
echo "[$(date)] uploads verified, stopping pod"
runpodctl stop pod "$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_POD_ID=//p')" \
  || echo "STOP FAILED - stop the pod manually"
