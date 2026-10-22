"""pix2db demo: image of a table / form / invoice / chart -> working SQLite database."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile

import gradio as gr

from pix2db import Pix2DB, from_sql

MODEL_ID = os.environ.get("PIX2DB_MODEL", "musapeker/pix2db-2b")

try:  # Hugging Face ZeroGPU
    import spaces
    gpu = spaces.GPU(duration=60)
except ImportError:  # local / CPU
    def gpu(fn):
        return fn

_model = None
# Outputs the model produced for the bundled examples (on GPU), so examples answer instantly on free CPU.
CACHE = json.load(open("examples/cache.json")) if os.path.exists("examples/cache.json") else {}


def image_key(image) -> str:
    return hashlib.md5(image.convert("RGB").tobytes()).hexdigest()


def model() -> Pix2DB:
    global _model
    if _model is None:
        import torch
        cuda = torch.cuda.is_available()
        _model = Pix2DB.from_pretrained(MODEL_ID, device_map="cuda" if cuda else "cpu",
                                        dtype=torch.bfloat16 if cuda else torch.float32)
    return _model


@gpu
def run_model(image) -> str:
    return model().generate(image)


def tables_html(ex) -> str:
    parts = []
    for name, df in ex.tables.items():
        parts.append(f"<h4 style='margin:12px 0 4px'>{name} <small>({len(df)} rows)</small></h4>")
        parts.append(df.to_html(index=False, border=0, classes="p2d"))
    return "".join(parts) or "<i>No tables.</i>"


def report_md(ex) -> str:
    lines = []
    if ex.repairs:
        lines.append("**Repairs applied:** " + "; ".join(sorted(set(ex.repairs))))
    if ex.errors:
        lines.append("**Statements dropped:**\n" + "\n".join(f"- `{e[:140]}`" for e in ex.errors))
    if ex.warnings:
        lines.append("**Checks:**\n" + "\n".join(f"- ⚠️ {w}" for w in ex.warnings))
    return "\n\n".join(lines) or "✅ SQL executed cleanly, all checks passed."


def extract(image):
    if image is None:
        raise gr.Error("Upload an image first.")
    raw = CACHE.get(image_key(image))
    if raw is None:
        gr.Info("Running the model on CPU — this can take 1–3 minutes on the free tier.")
        raw = run_model(image)
    ex = from_sql(raw)
    path = os.path.join(tempfile.mkdtemp(), "pix2db.sqlite")
    ex.save(path)
    first = next(iter(ex.tables), None)
    q = f'SELECT * FROM "{first}" LIMIT 20' if first else ""
    return ex.sql, tables_html(ex), report_md(ex), path, ex.sql, q


def run_query(sql_dump: str, query: str):
    if not sql_dump:
        raise gr.Error("Extract a database first.")
    try:
        return from_sql(sql_dump).query(query), ""
    except Exception as e:  # noqa: BLE001
        return None, f"❌ {e}"


CSS = ".p2d{border-collapse:collapse;font-size:13px}.p2d th,.p2d td{border:1px solid #ddd;padding:3px 8px}"

with gr.Blocks(title="pix2db", css=CSS) as demo:
    gr.Markdown(
        "# pix2db\n**Image → working SQLite database.** Upload a table, form, invoice, receipt or chart. "
        "A small VLM writes the schema (types, keys, foreign keys) and the rows; a verify/repair layer "
        "makes sure the SQL runs. Then query it with SQL.\n\n"
        "Examples answer instantly. Your own image runs on the free CPU (1–3 min) — for GPU speed use the "
        "[Colab notebook](https://colab.research.google.com/github/m-peker/pix2db/blob/main/notebooks/pix2db_colab.ipynb).")
    dump = gr.State("")
    with gr.Row():
        with gr.Column(scale=1):
            img = gr.Image(type="pil", label="Image", height=420)
            btn = gr.Button("Extract database", variant="primary")
            gr.Examples(examples=[[f"examples/{f}"] for f in sorted(os.listdir("examples")) if f.endswith(".png")]
                        if os.path.isdir("examples") else [], inputs=img, examples_per_page=12)
        with gr.Column(scale=1):
            with gr.Tab("Tables"):
                tabs = gr.HTML()
            with gr.Tab("SQL"):
                sql = gr.Code(language="sql", label="SQL dump")
            report = gr.Markdown()
            file = gr.File(label="Download .sqlite")
    gr.Markdown("### Query it")
    with gr.Row():
        query = gr.Textbox(label="SQL query", lines=2, scale=4)
        qbtn = gr.Button("Run", scale=1)
    qerr = gr.Markdown()
    qout = gr.Dataframe(label="Result")

    btn.click(extract, img, [sql, tabs, report, file, dump, query])
    qbtn.click(run_query, [dump, query], [qout, qerr])

if __name__ == "__main__":
    demo.launch()
