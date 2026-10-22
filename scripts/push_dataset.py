"""Pack generated splits into a Hugging Face dataset (parquet) and push it (private by default).

Usage: python scripts/push_dataset.py --repo musapeker/pix2db-data [--public]
"""
import argparse
import json
import sys
from pathlib import Path

from datasets import Dataset, DatasetDict, Features, Image, Value

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.scene import Scene  # noqa: E402

LEVEL_NAMES = {1: "clean", 2: "styled", 3: "hierarchical", 4: "document", 5: "scan", 6: "chart",
               7: "real_table", 8: "real_receipt", 9: "synthetic_receipt", 11: "real_table_unseen"}
SPLITS = {"train": "data/train", "validation": "data/val", "test": "data/test",
          "real_pubtabnet": "data/real_pubtabnet", "real_cord": "data/real_cord",
          # v2 additions
          "train_real": "data/real_train", "train_receipt": "data/receipt_train",
          "real_fintabnet": "data/real_fintabnet", "test_receipt": "data/test_receipt",
          "unseen_tabrecset": "data/unseen_tabrecset"}


def gen(d):
    for it in load_meta(d):
        sc = Scene.from_dict(it["scene"])
        yield {"image": str(Path(d) / "images" / f"{it['id']}.png"), "id": it["id"], "level": it["level"],
               "level_name": LEVEL_NAMES[it["level"]], "kind": it["kind"], "source_db": sc.db_id,
               "sql": sc.to_sql(), "scene": json.dumps(it["scene"], ensure_ascii=False),
               "num_tol_abs": float(it.get("num_tol_abs", 0.0)), "recall_only": bool(it.get("recall_only", False))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--public", action="store_true")
    args = ap.parse_args()
    feats = Features({"image": Image(), "id": Value("string"), "level": Value("int32"),
                      "level_name": Value("string"), "kind": Value("string"), "source_db": Value("string"),
                      "sql": Value("string"), "scene": Value("string"), "num_tol_abs": Value("float32"),
                      "recall_only": Value("bool")})
    dd = DatasetDict({k: Dataset.from_generator(gen, gen_kwargs={"d": v}, features=feats)
                      for k, v in SPLITS.items() if Path(v).exists()})
    print(dd)
    dd.push_to_hub(args.repo, private=not args.public, max_shard_size="500MB")
    print("pushed", args.repo)


if __name__ == "__main__":
    main()
