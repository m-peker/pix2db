#!/bin/bash
# One-shot setup of a fresh RunPod pod (runpod/pytorch torch 2.8 image). Idempotent.
set -e
mkdir -p /workspace/logs /workspace/pix2db
cat > /workspace/env.sh <<EOS
export HF_HOME=/workspace/.cache/huggingface
export PATH=/workspace/venv/bin:\$PATH
EOS
. /workspace/env.sh
[ -d /workspace/venv ] || python3 -m venv --system-site-packages /workspace/venv
pip install -q "transformers>=4.57" "peft>=0.17" "trl>=0.23" accelerate datasets qwen-vl-utils bitsandbytes \
  huggingface_hub pillow pandas playwright sqlglot gradio matplotlib scipy lxml html5lib beautifulsoup4 pyyaml
playwright install --with-deps chromium > /dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y -q fonts-roboto fonts-open-sans fonts-lato fonts-noto-core \
  fonts-crosextra-carlito fonts-crosextra-caladea fonts-ubuntu > /dev/null 2>&1 || true
fc-cache -f > /dev/null
if [ ! -d /workspace/vllm-venv ]; then
  python3 -m venv /workspace/vllm-venv
  /workspace/vllm-venv/bin/pip install -q vllm qwen-vl-utils ninja
fi
if [ ! -d /workspace/data/raw/spider/spider_data ]; then
  mkdir -p /workspace/data/raw/spider && cd /workspace/data/raw/spider
  hf download HAL-9001/spider-databases spider_data.zip --repo-type dataset --local-dir . > /dev/null
  unzip -q -o spider_data.zip && rm -f spider_data.zip
fi
echo SETUP_DONE
