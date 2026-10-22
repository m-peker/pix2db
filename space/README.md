---
title: pix2db
emoji: 🗃️
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
models:
  - musapeker/pix2db-2b
short_description: Image of a table, invoice, receipt or chart → SQLite DB
---

# pix2db demo

Upload a table, form, invoice, receipt or chart → get a working SQLite database, then query it.
Bundled examples answer instantly (outputs cached from a GPU run); your own image runs on the free CPU
(1–3 minutes). For GPU speed use the
[Colab notebook](https://colab.research.google.com/github/m-peker/pix2db/blob/main/notebooks/pix2db_colab.ipynb).

Example images: synthetic renders from this project, and real images from CORD (CC BY 4.0), PubTabNet and
FinTabNet (CDLA-Permissive-1.0) and TabRecSet (CC BY 4.0).

Model: [musapeker/pix2db-2b](https://huggingface.co/musapeker/pix2db-2b) · Code: [github.com/m-peker/pix2db](https://github.com/m-peker/pix2db)
