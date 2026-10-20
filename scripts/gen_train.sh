#!/bin/bash
# Generate the training split in 48 resumable shards, at most 24 at a time.
. /workspace/env.sh; cd /workspace/pix2db
S="/workspace/data/raw/spider/spider_data/database /workspace/data/raw/spider/spider_data/test_database"
COUNTS="1:2000,2:3500,3:5500,4:5000,5:5000,6:3000"
run_shard() {
  sleep $(( $1 % 24 ))
  python scripts/make_set.py --spider $S --dbs data/splits/train_dbs.txt --out data/train \
    --counts $COUNTS --shard $1 --num-shards 48 --prefix train_ >> /workspace/logs/gen_train_$1.log 2>&1
}
export -f run_shard; export S COUNTS
seq 0 47 | xargs -P 24 -I{} bash -c 'run_shard {}'
echo GENDONE
