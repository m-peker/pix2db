#!/bin/bash
# v2 data: restore v1 synthetic + real eval from the Hub, build real training data and receipts.
. /workspace/env.sh; cd /workspace/pix2db
L=/workspace/logs
SP="/workspace/data/raw/spider/spider_data/database /workspace/data/raw/spider/spider_data/test_database"
python scripts/pull_data.py --out data > $L/v2_pull.log 2>&1 &
python scripts/make_real_train.py --which pubtabnet --n 10000 --accept 1.0 --out data/real_train > $L/v2_ptn.log 2>&1 &
python scripts/make_real_train.py --which fintabnet --n 8000 --accept 1.0 --out data/real_train > $L/v2_fin.log 2>&1 &
python scripts/make_real_train.py --which cord --n 100000 --out data/real_train > $L/v2_cord.log 2>&1 &
python scripts/make_real_train.py --which fintabnet --split test --n 150 --accept 1.0 --out data/real_fintabnet > $L/v2_fintest.log 2>&1 &
for i in 0 1 2 3 4 5 6 7; do
  python scripts/make_set.py --spider $SP --dbs data/splits/train_dbs.txt --out data/receipt_train --counts 9:3000 \
    --shard $i --num-shards 8 --prefix rtrain_ > $L/v2_rec_$i.log 2>&1 &
done
python scripts/make_set.py --spider $SP --dbs data/splits/test_dbs.txt --out data/test_receipt --counts 9:150 \
  --seed 7 --prefix rtest_ > $L/v2_rectest.log 2>&1 &
wait
python scripts/check_gold.py real_train receipt_train real_fintabnet test_receipt > $L/v2_check.log 2>&1
echo GEN_V2_DONE
