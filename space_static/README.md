---
title: pix2db
emoji: 🗃️
colorFrom: blue
colorTo: green
sdk: static
app_file: index.html
pinned: false
license: apache-2.0
models:
  - musapeker/pix2db-2b
short_description: Image of a table, invoice, receipt or chart → SQLite DB
---

# pix2db demo

Upload a table, form, invoice, receipt or chart → get a working SQLite database, then query it.
Examples show cached outputs from a GPU run; the extracted SQLite database runs in your browser (sql.js), so you can query it live. To try your own image
use the
[Colab notebook](https://colab.research.google.com/github/m-peker/pix2db/blob/main/notebooks/pix2db_colab.ipynb).

Example images: synthetic renders from this project, and real images from CORD (CC BY 4.0), PubTabNet and
FinTabNet (CDLA-Permissive-1.0) and TabRecSet (CC BY 4.0).

Model: [musapeker/pix2db-2b](https://huggingface.co/musapeker/pix2db-2b) · Code: [github.com/m-peker/pix2db](https://github.com/m-peker/pix2db)

Paper (preprint): [PIX2DB: Reconstructing Executable Relational Databases from Document Images with a 2B Vision-Language Model](https://doi.org/10.21203/rs.3.rs-11467404/v1)
