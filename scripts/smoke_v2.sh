#!/bin/bash
. /workspace/env.sh; cd /workspace/pix2db
rm -rf data/smoke_v2
python scripts/make_real_train.py --which pubtabnet --n 4 --out data/smoke_v2 2>&1 | tail -1
python scripts/make_real_train.py --which fintabnet --n 4 --out data/smoke_v2 2>&1 | tail -1
python scripts/make_real_train.py --which cord --n 3 --out data/smoke_v2 2>&1 | tail -1
python scripts/make_set.py --spider /workspace/data/raw/spider/spider_data/database --dbs data/splits/train_dbs.txt \
  --out data/smoke_v2 --counts 9:4 2>&1 | tail -1
python scripts/check_gold.py smoke_v2 2>&1 | tail -3
ls data/smoke_v2/images
echo SMOKE_DONE
