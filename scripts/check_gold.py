"""Gold self-consistency: gold SQL must load without errors and score 1.0 against itself."""
import sys, collections
sys.path.insert(0, "src")
from pix2db.data import load_meta
from pix2db.scene import Scene
from pix2db.dbio import load_sql, read_db
from pix2db.metrics import score
for split in sys.argv[1:]:
    bad = collections.Counter(); n = 0
    for d in load_meta(f"data/{split}"):
        n += 1
        sc = Scene.from_dict(d["scene"]); lr = load_sql(sc.to_sql()); s = score(sc, read_db(lr.con), d["num_tol_abs"])
        if lr.n_errors or s["f1"] < 1 or s["table_exact"] < 1 or (s["type_acc"] or 1) < 1:
            bad[d["level"]] += 1
            if sum(bad.values()) <= 5: print("BAD", d["id"], lr.errors[:1], round(s["f1"], 3), s["table_exact"], s["type_acc"])
    print(split, n, "bad:", dict(bad))
