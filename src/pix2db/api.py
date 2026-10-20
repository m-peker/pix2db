"""Public API.

    from pix2db import Pix2DB
    model = Pix2DB.from_pretrained("musapeker/pix2db-2b")
    result = model.extract("invoice.png")
    print(result.sql)              # CREATE TABLE ... INSERT ...
    result.tables                  # {name: pandas.DataFrame}
    result.query("SELECT ...")     # pandas.DataFrame
    result.save("invoice.sqlite")  # write a real SQLite file
    result.warnings, result.repairs
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .prompts import SQL_PROMPT
from .repair import repair


@dataclass
class Extraction:
    sql: str
    raw_output: str
    con: sqlite3.Connection
    repairs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def tables(self) -> dict:
        import pandas as pd
        names = [r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {n: pd.read_sql_query(f'SELECT * FROM "{n}"', self.con) for n in names}

    def query(self, sql: str):
        import pandas as pd
        return pd.read_sql_query(sql, self.con)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        if path.exists():
            path.unlink()
        dst = sqlite3.connect(path)
        self.con.backup(dst)
        dst.close()
        return path


class Pix2DB:
    def __init__(self, model, processor, max_new_tokens: int = 3072):
        self.model = model
        self.processor = processor
        self.max_new_tokens = max_new_tokens

    @classmethod
    def from_pretrained(cls, name_or_path: str = "musapeker/pix2db-2b", device_map: str = "auto",
                        dtype: str = "auto", max_pixels: int = 1310720, **kw) -> "Pix2DB":
        from transformers import AutoModelForImageTextToText, AutoProcessor
        processor = AutoProcessor.from_pretrained(name_or_path, max_pixels=max_pixels)
        model = AutoModelForImageTextToText.from_pretrained(name_or_path, device_map=device_map, dtype=dtype, **kw)
        model.eval()
        return cls(model, processor)

    def generate(self, image) -> str:
        import torch
        from PIL import Image
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        image = image.convert("RGB")
        msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": SQL_PROMPT}]}]
        inputs = self.processor.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                                    return_dict=True, return_tensors="pt").to(self.model.device)
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)
        return self.processor.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    def extract(self, image) -> Extraction:
        raw = self.generate(image)
        return from_sql(raw)


def from_sql(text: str) -> Extraction:
    """Verify/repair a SQL dump (model output) and load it into an in-memory SQLite database."""
    rep = repair(text)
    return Extraction(rep.sql, text, rep.con, rep.repairs, rep.warnings, rep.errors)
