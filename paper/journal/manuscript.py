"""Manuscript text for the FAITH submission. Inline markup: <i>, <b>, <code>, <sup>, <sub>, [[cite keys]]."""

TITLE = ("PIX2DB: Reconstructing Executable Relational Databases from Document Images with a 2B "
         "Vision-Language Model")
AFFILIATION = ("Ozveri R&amp;D Center, Ozdilek Home Textile Industry and Trade Inc., [postal address], Bursa, "
               "Türkiye; e-mail: msapeker@gmail.com")
CORRESPONDING = "Corresponding Author: Musa Peker (msapeker@gmail.com)"
KEYWORDS = ("Document understanding; Image-to-SQL; Relational schema reconstruction; Synthetic data; "
            "Table extraction; Vision-language models")
ABSTRACT = (
    "Much operational data reaches organizations as images: screenshots of spreadsheets, scanned statements, "
    "photographed receipts and charts. Current extraction methods return a cell grid or HTML that keeps the layout "
    "but leaves the relational decisions open: merged cells stay merged, a document header and its line items stay "
    "unrelated, and formatted numbers remain strings. This study defines image-to-database reconstruction, in which "
    "a model must turn one image into a SQLite dump whose tables, column types, primary and foreign keys and rows "
    "load and can be queried directly. Training data with exact gold databases is produced by rendering samples of "
    "the Spider databases at six layout levels and by converting PubTabNet, FinTabNet and CORD annotations under the "
    "same normalization rules. A 2B-parameter model, Qwen3-VL-2B adapted with LoRA on 36,589 image-dump pairs and "
    "followed by a deterministic verify-and-repair layer, is compared with Qwen3-VL models of 2B, 4B and 8B "
    "parameters and with an HTML-to-SQLite pipeline. On rendered tables from unseen databases it reaches 0.86 table "
    "exact match and 0.99 foreign-key recall, against 0.75 and 0.75 for the 8B model prompted for SQL. On held-out "
    "real images it obtains cell F1 of 0.81 (PubTabNet) and 0.96 (FinTabNet) and cell recall of 0.93 on receipt "
    "photographs. On TabRecSet, a source not used for training, it is the strongest system that writes a database "
    "directly (0.52) but trails the 8B HTML pipeline (0.58), mainly in reading photographed text. The results show "
    "that the relational conventions are learned reliably by a small model, whereas robust reading of unfamiliar "
    "images still benefits from larger encoders.")


def write(g):
    H1, H2, H3, P, PC, LEAD, BUL, NUM, BACK = (g[k] for k in ["H1", "H2", "H3", "P", "PC", "LEAD", "BUL", "NUM", "BACK"])
    figure, table, equation, algorithm, N = g["figure"], g["table"], g["equation"], g["algorithm"], g["N"]
    mr, frac, sub, nsum, paren = g["mr"], g["frac"], g["sub"], g["nsum"], g["paren"]
    tex_rows, clean, para = g["tex_rows"], g["clean"], g["para"]
    FIG = g["HERE"] / "fig"

    # ================================================================== 1. Introduction
    H1("1. Introduction")
    P("Tabular data is often available only as a picture. Spreadsheets are shared as screenshots, financial "
      "statements arrive as scanned PDFs, purchase records exist as photographs of receipts, and dashboards are "
      "circulated as rendered charts. Before such data can be joined, filtered or summed, it has to be turned back "
      "into records. This is the research object of the present study: the reconstruction of a relational database "
      "from a single document image.")
    P("Existing work approaches the problem from the layout side. Table structure recognition (TSR) predicts the "
      "grid of a cropped table, from early convolutional detectors [[schreiber2017deepdesrt,paliwal2019tablenet,"
      "prasad2020cascadetabnet]] to image-to-sequence and transformer models trained on large corpora "
      "[[zhong2020pubtabnet,smock2022pubtables,nassar2022tableformer]]. OCR-free document models parse pages into "
      "markup without a separate text recognizer [[kim2022donut,lee2023pix2struct,blecher2023nougat,wei2024got,"
      "poznanski2025olmocr]], and chart models translate plots into linearized tables [[liu2023deplot]]. These "
      "methods are strong at describing how a table <i>looks</i>: TSR models recover row and column spans "
      "accurately, and general vision-language models (VLMs) read printed text well. Their weakness is that the "
      "output is still a layout. Turning it into something a program can query requires decisions that markup "
      "leaves open: which rows a merged cell belongs to, how a two-level header becomes a column name, whether "
      "\"(1,209)\" is a negative number, and which of two tables on a page refers to the other.")
    P("The problem addressed here is therefore not table recognition but the relational step that follows it, "
      "performed directly from pixels. Prompting a general model does not solve it. In a pilot study with 150 "
      "rendered images, Qwen3-VL-8B [[bai2025qwen3vl]] produced an executable SQL dump for 93% of the images but a "
      "completely correct table for only 61%; the same model asked for HTML, converted to SQLite by a short script, "
      "reached 46% and failed precisely on merged cells and forms. The errors were rarely misread characters. The "
      "models placed merged values in a single row, invented header tables, omitted foreign keys, or wrote a name "
      "such as <code>O'Brien</code> without escaping, so that one malformed row invalidated an entire statement. The "
      "closest prior work, OptiSQL [[li2026optisql]], generates one SQL query per question from a clean table image "
      "and never reconstructs the database.")
    P("This study proposes PIX2DB, a 2B-parameter model that writes the relational decisions into its output. "
      "Given an image, it produces a SQLite dump: <code>CREATE TABLE</code> statements with column types, primary "
      "and foreign keys, followed by <code>INSERT</code> statements for every record. A deterministic "
      "verify-and-repair layer executes the dump, repairs common syntactic failures and reports suspicious content. "
      "Figure 1 shows a rendered document from a database that was not used for training and the dump written by the "
      "model. The main contributions are:")
    NUM(["A task definition for image-to-database reconstruction with explicit normalization conventions, and an "
         "evaluation protocol that aligns predicted and gold databases without relying on table or column names.",
         "A data construction method that yields exact gold databases at scale, by rendering samples of real "
         "relational databases at controlled layout difficulty and by converting existing table and receipt "
         "annotations into the same conventions, with every gold dump verified by execution.",
         "PIX2DB-2b, a LoRA-adapted 2B model with a deterministic repair layer, which outperforms models of the same "
         "family with four times more parameters on five of six evaluation sets and recovers foreign keys almost "
         "perfectly.",
         "An analysis of what transfers: rendered layouts teach the conventions but not robust reading, a modest set "
         "of converted real tables closes most of the real-image gap, and on a held-out source the remaining gap is "
         "reading accuracy rather than structure."])
    figure(FIG / "teaser.png", "A rendered document from a database not used for training (a) and the SQLite dump "
           "written by PIX2DB (b). The key–value header becomes its own table, the merged <i>Owner user id</i> cell "
           "is repeated in every item row, and the relation between the two blocks is stated as a foreign key.")
    P("The rest of the paper is organized as follows. Section 2 reviews related work. Section 3 defines the task and "
      "describes the data construction, the model, the repair layer and the evaluation protocol. Section 4 reports "
      "the experiments and discusses the results. Section 5 compares PIX2DB with the state of the art, and "
      "Section 6 concludes.")

    # ================================================================== 2. Related Work
    H1("2. Related Work")
    H2("2.1. Table Structure Recognition")
    P("Table detection and structure recognition have a long history in document analysis, with benchmark "
      "competitions such as ICDAR 2013 [[gobel2013icdar]] and layout corpora such as PubLayNet "
      "[[zhong2019publaynet]]. Deep models moved from detecting rows and columns with convolutional networks "
      "[[schreiber2017deepdesrt,paliwal2019tablenet,prasad2020cascadetabnet]] to predicting full structure "
      "sequences. PubTabNet [[zhong2020pubtabnet]] introduced 568k scientific tables with HTML annotations and the "
      "tree-edit-distance score TEDS; FinTabNet [[zheng2021gte]] added tables from financial reports, and "
      "PubTables-1M [[smock2022pubtables]] and the corrected FinTabNet.c [[smock2023aligning]] improved annotation "
      "consistency. SciTSR [[chi2019scitsr]] targets complicated scientific tables, while WTW [[long2021wtw]] and "
      "TabRecSet [[yang2023tabrecset]] cover photographed tables in the wild. TableFormer "
      "[[nassar2022tableformer]] and the PubTables-1M detector predict structure and rely on PDF text or OCR for "
      "content. A grid is a faithful description of the layout, not of the data: TEDS rewards reproducing a "
      "rowspan, whereas a database must resolve it into repeated values.")
    H2("2.2. OCR-Free Document Models and Charts")
    P("Layout-aware pre-training such as LayoutLM [[xu2020layoutlm]] and LayoutLMv3 [[huang2022layoutlmv3]] "
      "combines OCR tokens with visual features. Donut [[kim2022donut]] and Pix2Struct [[lee2023pix2struct]] showed "
      "that an image-to-sequence model can parse documents without an OCR stage, and Nougat "
      "[[blecher2023nougat]], GOT [[wei2024got]], olmOCR [[poznanski2025olmocr]] and Docling [[auer2024docling]] "
      "convert pages into Markdown, LaTeX or HTML. General VLMs such as Qwen3-VL [[bai2025qwen3vl]] read tables "
      "well enough to be the strongest baselines in this study. For charts, DePlot [[liu2023deplot]], MatCha "
      "[[liu2023matcha]] and UniChart [[masry2023unichart]] translate plots into linearized tables, evaluated on "
      "ChartQA [[masry2022chartqa]] and PlotQA [[methani2020plotqa]]. None of these models targets a typed "
      "relational schema or relations between tables; here a chart is treated as one more layout whose target is "
      "a typed table.")
    H2("2.3. Tables, Images and SQL")
    P("Text-to-SQL research assumes that the database already exists. Benchmarks such as Spider [[yu2018spider]], "
      "BIRD [[li2023bird]] and Spider 2.0 [[lei2025spider2]] pair questions with databases, and methods improve "
      "schema linking [[wang2020ratsql]], constrain decoding to valid SQL [[scholak2021picard]] or let the model "
      "correct its own queries [[pourreza2023dinsql]]. Visual table question answering [[zheng2024multimodal,"
      "singh2025mtabvqa,mathew2021docvqa]] answers questions over images, and recent analyses report that VLMs "
      "degrade sharply on noisy real-world tables [[singh2025lost]]. OptiSQL [[li2026optisql]] renders Spider 2.0 "
      "tables and generates an executable query from the image and a question; MTabVQA [[singh2025mtabvqa]] renders "
      "Spider and BIRD tables for multi-table question answering. The present study also renders Spider databases, "
      "but the database itself is the output, so that any number of queries can later run on it. Rendering training "
      "data with free and exact labels follows a long tradition in text recognition [[gupta2016synthtext]].")

    # ================================================================== 3. Proposed Method
    H1("3. Proposed Method")
    P("Figure 2 gives an overview. Training pairs of an image and its gold SQLite dump are built from two sources: "
      "rendered samples of real relational databases and converted annotations of real table and receipt images. A "
      "2B VLM is adapted with LoRA to write the dump, and at inference time its output passes through a "
      "verify-and-repair layer before it is loaded into SQLite.")
    figure(FIG / "method.png", "Overview of PIX2DB: training data construction (top) and inference (bottom).")
    H2("3.1. Task Definition")
    P("For an image <i>I</i>, the system outputs a SQL text <i>D</i>. The prediction is the database obtained by "
      "executing the <code>CREATE TABLE</code> and <code>INSERT</code> statements of <i>D</i> in an empty SQLite "
      "instance; other statements are ignored. The target follows fixed conventions:")
    BUL(["one row per record, with the value of a merged cell repeated in every row it covers;",
         "multi-level headers joined into one snake_case column name;",
         "numbers stored without thousand separators or currency signs, accounting negatives such as \"(1,209)\" as "
         "negative numbers, and dates in ISO form;",
         "empty cells as NULL and derived totals rows not stored;",
         "one table per logical block, with a foreign key from line items to their header;",
         "for charts, the category column and one column per data series."])
    P("Table and column names are chosen by the model and are not scored, because the same data can be named in "
      "many reasonable ways.")
    H2("3.2. Training Data Construction")
    H3("3.2.1. Rendering databases")
    P("A <i>scene</i> is a small database cut from one of the Spider [[yu2018spider]] SQLite files (CC BY-SA 4.0): a "
      "single table with 3–25 sampled rows and 3–9 columns, two unrelated tables, or a parent row together with "
      "3–15 child rows that reference it through a declared foreign key. Columns with long or mostly empty values "
      "are dropped, numeric strings and integer-valued floats are coerced to numbers, and composite primary keys are "
      "not declared. Scenes are rendered with HTML and CSS in a headless browser at six levels (Figure 3):")
    BUL(["<b>L1 clean</b>: a plain grid with raw column names;",
         "<b>L2 styled</b>: 17 font families, colored or zebra styling, humanized headers in four case styles, "
         "thousand separators (never on identifiers or years), currency prefixes on money-like columns and long-form "
         "dates;",
         "<b>L3 hierarchical</b>: merged cells on a repeated grouping column, two-level headers that group textual "
         "and numeric columns, transposed layouts for small tables and occasional derived totals rows;",
         "<b>L4 document</b>: a parent row rendered as a key–value block above the child table;",
         "<b>L5 scan</b>: L3 and L4 pages degraded with rotation up to ±2.5°, uneven lighting, sensor noise, blur, "
         "contrast change, optional grayscale and JPEG quality 45–80;",
         "<b>L6 chart</b>: bar, horizontal bar, line and pie charts with one to three series, printing value labels "
         "for 60% of the charts whose labels are exact."])
    P("Synthetic receipts use narrow monospaced layouts with three item-line formats, modifiers such as \"less "
      "sugar\", subtotal, tax and payment lines, and are photographed 85% of the time. Two invariants keep the gold "
      "exact. Every displayed string maps back to the gold value without loss: formatting adds separators or "
      "symbols but never rounds or truncates. Because rendering may reorder rows and columns, for example to group "
      "merged cells, the gold scene is reordered in the same way, so the target dump follows the reading order of the "
      "image. Splits are made by database: the 146 Spider training databases feed training, the 20 development "
      "databases validation, and the 40 databases that appear only in Spider's test set form the synthetic test.")
    figure(FIG / "renders.png", "One rendered example per synthetic level, all from the validation databases. For the "
           "receipt the gold database is a single <i>items</i> table; the subtotal, tax and payment lines are not "
           "stored.")
    H3("3.2.2. Converting real annotations")
    P("PubTabNet [[zhong2020pubtabnet]] and FinTabNet [[zheng2021gte]] (both CDLA-Permissive-1.0) annotate table "
      "images with HTML. The converter expands spans into a grid, flattens header rows into names, repeats body "
      "rowspans, converts numbers as above and maps lone dashes to NULL. In the HTML release of FinTabNet used here, "
      "tables carry no explicit header element, so the first row is taken as the header, and the second as well when "
      "the first contains group colspans; the original FinTabNet annotations are used rather than FinTabNet.c "
      "[[smock2023aligning]]. Tables whose body contains colspans, typically section rows such as \"Assets\", have "
      "no unambiguous relational form and are rejected, as are tables with more than 30 rows or 10 columns. Of the "
      "streamed training tables, 72% of PubTabNet and 69% of FinTabNet pass. CORD [[park2019cord]] receipts "
      "(CC BY 4.0) become an <i>items</i> table with name, quantity and price, built from the menu annotations.")
    H3("3.2.3. Execution check and dataset statistics")
    P("Every gold dump, synthetic or converted, is executed and scored against itself; any score below 1.0 indicates "
      "a defect in the data. The check found composite keys declared as primary keys, numbers stored as text in "
      "Spider, identifiers that start with a digit or are SQL keywords (these are now quoted), empty strings in "
      "numeric columns, and one header-deduplication collision in a converted table, which was removed. Table 1 "
      "lists all splits; every split is publicly released.")
    data_rows = [[clean(c) for c in r] for r in tex_rows("data.tex")]
    table(["Split", "Images", "Tables per image", "Rows", "Columns", "With FK"], data_rows,
          [2257, 1100, 1420, 1020, 1030, 1030],
          "Dataset splits. Rows and columns are averages per table; \"With FK\" is the share of images whose gold "
          "database contains a foreign key.", head_size=16)
    H2("3.3. Model and Training")
    P("PIX2DB-2b is Qwen3-VL-2B-Instruct [[bai2025qwen3vl]] adapted with low-rank adaptation (LoRA) "
      "[[hu2022lora,dettmers2023qlora]]. For every linear projection <i>W</i> of the language model (attention "
      "query, key, value and output, and the MLP gate, up and down projections), the frozen weight is complemented "
      "by a trainable low-rank update, as shown in Eq. (1):")
    equation(mr("W") + mr("′", True) + mr("=") + mr("W") + mr("+") + frac(mr("α"), mr("r")) + mr("B") + mr("A"))
    PC("where <i>B</i> ∈ ℝ<sup>d×r</sup> and <i>A</i> ∈ ℝ<sup>r×k</sup> with rank <i>r</i> = 64 and scaling "
       "<i>α</i> = 128; <i>B</i> is initialized to zero so that training starts from the base model, and the "
       "vision encoder is not adapted. The model receives the image <i>I</i> and a fixed instruction <i>x</i> "
       "(Appendix A) and is trained to generate the gold dump <i>y</i>. The loss is the token-level cross-entropy "
       "over the answer tokens only, as given in Eq. (2):")
    equation(mr("ℒ") + paren(mr("θ")) + mr("=") + mr("−") + frac(mr("1"), mr("|Y|")) +
             nsum(mr("t∈Y"), mr("log ", True) + sub(mr("p"), mr("θ")) +
                  paren(sub(mr("y"), mr("t")) + mr(" | ") + sub(mr("y"), mr("<t")) + mr(", I, x"))))
    PC("where <i>Y</i> is the set of positions of the SQL answer; image and instruction tokens and padding are "
       "masked out. Training mixes 14,000 synthetic images (all six levels), 3,000 synthetic receipts, 9,999 "
       "PubTabNet and 8,000 FinTabNet tables, and 795 CORD receipts seen twice, for a total of 36,589 examples. "
       "Images are resized to at most 1.31 MP (about 1,280 visual tokens). Optimization uses AdamW with a learning "
       "rate of 10<sup>−4</sup>, cosine decay, 3% warm-up, an effective batch of 16, bf16 precision and one epoch "
       "(2,287 steps, 5.9 h on one NVIDIA A40). A per-device batch of 8 exhausted memory on long batches because of "
       "the full-vocabulary logits, so a batch of 4 with gradient accumulation of 4 was used. After training, the "
       "update of Eq. (1) is merged into the base weights.")
    H2("3.4. Verify-and-Repair Layer")
    P("The model output passes through a deterministic layer before it is returned (Algorithm 1). Statements are "
      "executed one at a time. A failing statement is retried after escaping apostrophes inside words, quoting or "
      "rewriting identifiers that are SQL keywords or free text (for example <code># of sequences¹</code> becomes "
      "<code>of_sequences</code>), and, for <code>INSERT</code> statements, inserting row by row with bare "
      "composite values such as <code>9 (8)</code> or <code>85.0 ± 10.8</code> quoted as text and missing "
      "trailing cells padded with NULL. A primary key that rejects duplicate values is dropped rather than the rows. "
      "Truncated output keeps its complete tuples. Remaining problems are reported rather than hidden: empty "
      "tables, values that contradict their declared type, duplicate rows and foreign keys without a parent. "
      "Statements that execute are left unchanged, except that a primary key is dropped when later rows violate it. "
      "The layer is related in spirit to constrained decoding [[scholak2021picard]] and self-correction "
      "[[pourreza2023dinsql]] in text-to-SQL, but it operates after generation and needs no additional model call.")
    algorithm("Verify-and-repair of a generated SQLite dump",
              "model output <i>D</i> (SQL text)",
              "SQLite database <i>S</i>, list of applied repairs <i>R</i>, list of warnings <i>W</i>",
              [(0, "Split <i>D</i> into statements; if the last statement is incomplete, keep its complete tuples"),
               (0, "<b>for each</b> statement <i>s</i> of type CREATE TABLE or INSERT <b>do</b>"),
               (1, "<b>if</b> <i>s</i> executes in <i>S</i> <b>then continue</b>"),
               (1, "try, in order: escape apostrophes; quote keyword identifiers; rename free-text identifiers"),
               (1, "<b>if</b> a variant executes <b>then</b> add the repair to <i>R</i>; <b>continue</b>"),
               (1, "<b>if</b> a UNIQUE constraint fails <b>then</b> drop the primary key of that table and retry"),
               (1, "<b>if</b> <i>s</i> is INSERT <b>then</b> insert row by row, quoting bare values and padding "
                   "missing trailing cells; drop rows that still fail"),
               (1, "<b>if</b> <i>s</i> still fails <b>then</b> record the error"),
               (0, "Check <i>S</i>: empty tables, type violations, duplicate rows, dangling foreign keys → <i>W</i>"),
               (0, "<b>return</b> <i>S</i>, <i>R</i>, <i>W</i>")])
    H2("3.5. Evaluation Protocol")
    P("Cell values are normalized before comparison: Unicode NFKC, unified dash variants, numbers parsed after "
      "removing separators and currency signs, common date formats mapped to ISO, and strings case-folded; empty "
      "values are ignored. For a gold table <i>G</i> and a predicted table <i>P</i>, columns are aligned by a "
      "maximum-weight bipartite matching whose weights are the multiset overlap of normalized column values, and rows "
      "by a second matching whose weights count agreeing aligned cells, both solved with the Hungarian method "
      "[[kuhn1955hungarian]]. The resulting number of agreeing cells <i>a</i>(<i>G</i>, <i>P</i>) is used to match "
      "gold tables to predicted tables, again by maximum-weight assignment <i>π</i>. Cell precision and recall are "
      "defined in Eq. (3):")
    equation(mr("Prec") + mr("=") + frac(nsum(mr("k"), mr("a") + paren(sub(mr("G"), mr("k")) + mr(", ") + sub(mr("P"), mr("π(k)")))), sub(mr("N"), mr("pred", True))) +
             mr(",   ") + mr("Rec") + mr("=") + frac(nsum(mr("k"), mr("a") + paren(sub(mr("G"), mr("k")) + mr(", ") + sub(mr("P"), mr("π(k)")))), sub(mr("N"), mr("gold", True))))
    PC("where <i>N</i><sub>pred</sub> and <i>N</i><sub>gold</sub> are the numbers of non-empty predicted and gold "
       "cells. Cell F1 is their harmonic mean, given in Eq. (4):")
    equation(mr("F1") + mr("=") + frac(mr("2·Prec·Rec"), mr("Prec+Rec")))
    PC("<i>Table exact match</i> requires a matched table with the same number of rows and columns and every gold "
       "cell recovered. <i>FK recall</i> is the fraction of gold foreign keys whose child and parent tables are "
       "matched to predicted tables connected by a declared foreign key. <i>Type accuracy</i> counts an aligned "
       "column as correct when its declared SQLite affinity and the stored values agree with the gold column being "
       "numeric or textual. Two cases are relaxed. Values of charts drawn without value labels match within the "
       "tolerance of Eq. (5):")
    equation(mr("|") + mr("v̂") + mr("−") + mr("v") + mr("|") + mr("≤") + mr("τ") + mr(",   ") + mr("τ") + mr("=") +
             mr("0.04") + mr("·") + sub(mr("max", True), mr("i")) + mr("|") + sub(mr("v"), mr("i")) + mr("|"))
    PC("and receipts are scored by recall, because a correct database may legitimately contain an extra table for "
       "totals or payment.")

    # ================================================================== 4. Results and Discussion
    H1("4. Results and Discussion")
    H2("4.1. Experimental Setup")
    P("All experiments were run on a single NVIDIA A40 (48 GB) with PyTorch 2.8, Hugging Face Transformers and PEFT "
      "for training, and vLLM [[kwon2023vllm]] for inference. PIX2DB is compared with Qwen3-VL-2B, 4B and "
      "8B-Instruct given the same instruction (Appendix A), and with a two-stage pipeline in which Qwen3-VL-8B "
      "outputs HTML tables that keep row and column spans and a script loads them with <code>pandas.read_html</code>, "
      "which expands spans, into SQLite. All SQL outputs, those of PIX2DB and of the baselines, go through the same "
      "repair layer. Decoding is greedy with at most 3,072 new tokens and the same image budget for all systems.")
    P("Besides the synthetic test (150 images per level), held-out splits of the real sources are used: 150 "
      "PubTabNet and 150 FinTabNet validation tables and 60 CORD test receipts with at least two items, together with "
      "150 synthetic receipts. These images are unseen, but their style is familiar from training. To measure "
      "transfer, TabRecSet-150 was built from TabRecSet [[yang2023tabrecset,tabrecsetdata]] (CC BY 4.0), which was not "
      "used for training; because it has been public since 2022 it may have been part of the base model's "
      "pre-training. Only English original images are taken (not the generated three-line and no-line variants, "
      "which repeat the same tables), one table per image, cropped by its cell polygons and with at least 60% "
      "non-empty cells. TabRecSet does not mark header rows, so the first grid row is used as header; 64% of the "
      "inspected tables pass the conversion rules. Its annotators wrote illegible characters as <code>#</code>, and "
      "these are kept in the gold (94 of 4,199 cells, in 26 tables); removing them from scoring changes cell F1 by "
      "less than 0.01 for every system and leaves the ranking unchanged. Some images contain handwriting and three "
      "cells contain Chinese characters; neither was filtered. 95% confidence intervals come from 2,000 bootstrap "
      "resamples of evaluation items, and <i>p</i>-values from a one-sided paired bootstrap against the strongest "
      "competitor on each set.")
    H2("4.2. Main Results")
    main = [[clean(c) for c in r] for r in tex_rows("main.tex")]
    main[0][0] = "PIX2DB-2b (ours)"
    table(["System", "Synthetic\nexact", "PubTabNet\nF1", "FinTabNet\nF1", "CORD\nrecall", "Receipts\nrecall",
           "TabRecSet\nF1", "FK\nrecall"], main, [1689, 881, 881, 881, 881, 881, 881, 882],
          "Main results with 95% bootstrap intervals. Synthetic: table exact match on 900 images from unseen "
          "databases; PubTabNet, FinTabNet and TabRecSet: cell F1; CORD and synthetic receipts (Receipts): cell recall; FK "
          "recall on the synthetic test images that contain a foreign key. Best value per column in bold.",
          footer="Against the best competitor on each set, PIX2DB is ahead with p &lt; 0.001 on synthetic, FinTabNet, "
                 f"CORD and synthetic receipts and with p = {N['prealpubtabnet']} on PubTabNet; on TabRecSet the 8B "
                 "HTML pipeline is ahead by 0.06 (paired 95% interval of the difference [0.03, 0.09], p &lt; 0.001; "
                 "Wilcoxon signed-rank p &lt; 0.001).", size=16, head_size=14)
    P(f"Table 2 gives the overall picture. Fine-tuning moves the 2B model from the bottom of the table to the top "
      f"on every set except TabRecSet. On the synthetic test it gains 33 points of exact match over its own base "
      f"model and 11 points over the 8B model; on FinTabNet and CORD the margins over the strongest competitor are 9 "
      f"and 14 points. PubTabNet is the closest case: the HTML pipeline, which suits flat scientific tables, is 3 "
      f"points behind and the difference is not significant at the 5% level. Foreign keys separate the systems most "
      f"clearly. PIX2DB declares {N['fkours']} of the gold relations, the 8B model prompted for SQL "
      f"{N['fkEightbsql']}, the smaller models about a quarter, and the HTML pipeline none, because nothing in HTML "
      f"expresses a relation between two tables.")
    H2("4.3. Effect of Layout Difficulty")
    figure(FIG / "levels.png", "Table exact match per synthetic level (150 images each). The HTML pipeline is "
           "competitive on flat tables and loses most of its accuracy once merged cells, forms or scanning are "
           "involved.")
    P(f"Figure 4 breaks the synthetic test down by level. On flat tables (L1, L2) all systems are within a few points "
      f"of each other, and the HTML pipeline reaches {N['lvhtmla']} and {N['lvhtmlb']}. With merged cells, key–value "
      f"headers and photographed pages it falls to {N['lvhtmlc']}, {N['lvhtmld']} and {N['lvhtmle']}, whereas PIX2DB "
      f"stays at {N['lvoursc']}, {N['lvoursd']} and {N['lvourse']}. The HTML stage itself is mostly right; the failure "
      f"lies in the conversion, which has no notion that a rowspan is a grouping key or that a form above a table is "
      f"a separate record. Charts are the exception to this pattern: apart from the untuned 2B model, all systems lie "
      f"between 0.57 and 0.63 exact match, and PIX2DB ({N['lvoursf']}) is not better than the 8B model. Charts without "
      f"value labels are harder (0.52 exact against 0.69 with labels), but labeled charts still fail in almost a third "
      f"of cases, so the difficulty lies as much in assigning marks to categories and series as in estimating values.")
    H2("4.4. Contribution of Real Training Data")
    figure(FIG / "ablation_data.png", "The same model and recipe trained on synthetic data only (v1) or with the "
           "converted real tables and receipts added (v2). Metrics as in Table 2.", 0.62)
    P(f"A first version, otherwise identical, was trained on 24,000 synthetic images only. Figure 5 shows that it "
      f"reaches the same synthetic accuracy ({N['vonetest']} against {N['ourstest']}) but transfers poorly: cell F1 "
      f"{N['vonerealpubtabnet']} on PubTabNet, {N['vonerealfintabnet']} on FinTabNet and recall {N['vonerealcord']} on "
      f"CORD. Its failures on PubTabNet were rarely layout errors. In 82 of 150 outputs the SQL did not execute at all "
      f"(28 after repair), mostly because composite values such as <code>9 (8)</code> or <code>85.0 ± 10.8</code> "
      f"were written as bare numbers, a format that never occurs in Spider; in other cases the model looped on a "
      f"<code>CREATE TABLE</code> statement it could not finish. Adding 18,794 converted real tables and receipts "
      f"removes these failures without costing synthetic accuracy and lifts TabRecSet from {N['voneunseentabrecset']} "
      f"to {N['oursunseentabrecset']}. The synthetic data teaches the conventions; the real data teaches what real "
      f"cell contents look like.")
    H2("4.5. Effect of the Repair Layer")
    figure(FIG / "ablation_repair.png", "Share of executable outputs and cell F1 before and after the repair layer, "
           "pooled over all evaluation sets.", 0.62)
    P(f"Figure 6 pools all six sets. The layer raises the share of outputs that execute from {N['repoursexecraw']} to "
      f"{N['repoursexecrep']} for PIX2DB and from {N['repTwobexecraw']} to {N['repTwobexecrep']} for the untuned 2B "
      f"model, but it moves pooled cell F1 by at most four points. Its value lies in the tail: on TabRecSet, where "
      f"PIX2DB is out of distribution, execution rises from 0.91 to 0.99, and on PubTabNet F1 improves by 3 points "
      f"(Appendix B, Table A1). The repair layer is no substitute for training: applied to the base model it leaves F1 "
      f"at {N['repTwobfOnerep']}, far below the fine-tuned model without repair ({N['repoursfOneraw']}).")
    H2("4.6. Error Analysis on an Unseen Source")
    figure(FIG / "errors_tabrecset.png", f"Outcome categories on TabRecSet-150, a source not used for training. The "
           f"thin orange segment is the key–value category ({N['errourskeyvalue']}, {N['errEightbhtmlkeyvalue']} and "
           f"{N['errEightbsqlkeyvalue']} tables from top to bottom); each row sums to 150.", 0.62)
    P(f"TabRecSet-150 is the only set on which PIX2DB loses ({N['oursunseentabrecset']} against "
      f"{N['Eightbhtmlunseentabrecset']}). Each prediction was assigned to one category (Figure 7): F1 of at least "
      f"0.9; usable output with the right number of rows but wrong cell contents; a wrong number of rows; a "
      f"two-column key–value table; or no usable output. Key–value layouts, for which the first-row-as-header gold is "
      f"questionable, account for only {N['nkv']} tables and do not explain the gap. The largest bucket for all systems "
      f"is cell content ({N['errourscell']} for PIX2DB, {N['errEightbhtmlcell']} for the HTML pipeline): the rows are "
      f"found but text in photographed, skewed or low-resolution tables is misread. PIX2DB also segments rows wrongly "
      f"more often ({N['erroursrow']} against {N['errEightbhtmlrow']}). The "
      f"8B model reads these images better than the 2B model it is compared with, and the HTML route spends no "
      f"capacity on normalization. On this source the bottleneck is reading, which points to a larger base model as "
      f"the next step rather than more synthetic layouts.")
    H2("4.7. Column Types and Cost")
    types = [[clean(c) for c in r] for r in tex_rows("types.tex")]
    types[0][0] = "PIX2DB-2b (ours)"
    for r in types[1:]:
        r[0] = "Qwen3-VL-" + r[0]
    table(["System", "Type accuracy", "SQL executes\n(raw)", "Output tokens", "Seconds per\nimage"], types,
          [2657, 1300, 1300, 1300, 1300],
          "Column types and cost on the synthetic test. Type accuracy over aligned columns (after repair), share of "
          "raw outputs that execute, mean output tokens and amortized seconds per image with vLLM on one A40.")
    P(f"Table 3 adds column types and output size on the synthetic test. Stored types are almost always right for "
      f"every SQL system; the HTML pipeline reaches 0.89 because pandas infers types from formatted strings, so "
      f"\"$1,250\" stays text. PIX2DB writes the shortest outputs ({N['tokours']} tokens on average, against "
      f"{N['tokhtml']} for HTML), which together with its size makes it the fastest system: 0.09 s per image amortized "
      f"over a vLLM batch on one A40. Training and every evaluation in this study used about 12 GPU-hours.")
    H2("4.8. Discussion")
    P("<i>Conventions are cheap to learn; reading is not.</i> The decisions that turn a layout into a database are "
      "few and regular. General VLMs know them but apply them inconsistently: the 8B model declares three quarters of "
      "the foreign keys and resolves merged cells correctly about two times in three. A small model trained on a few "
      "tens of thousands of exact examples applies them almost every time. Reading text is different. The "
      "synthetic-only model read rendered text well and real text poorly, and on TabRecSet a larger general model "
      "still reads better than the fine-tuned small one. The recipe is expected to carry over to a 4B or 8B base with "
      "little change, and the TabRecSet gap to shrink accordingly.")
    P("<i>Validity of the evaluation.</i> The metric ignores names, so a schema with unhelpful column names scores as "
      "well as a good one; naming quality is not measured. The real held-out sets share their sources with the "
      "training data and therefore overstate performance on unfamiliar documents, which is why TabRecSet is reported "
      "separately. TabRecSet's missing header annotation forces a header assumption that is wrong for some tables, "
      "although the error analysis shows that it affects few. All numbers come from a single training run; the "
      "intervals reflect the sampling of test items, not training variance.")
    P("<i>Limitations.</i> Handwriting, multi-page tables and tables longer than 30 rows are outside the training "
      "distribution. Tables whose body contains section rows were excluded from both training and evaluation, so the "
      "behavior of the model on them is unknown. Charts without value labels are read approximately. The data is "
      "English, apart from a few TabRecSet cells. Receipts and invoices may contain personal data; the released data "
      "uses public datasets whose images were collected and anonymized by their authors. Extraction errors are likely "
      "to look plausible, so the warnings reported by the repair layer should be shown to users rather than "
      "discarded.")

    # ================================================================== 5. Comparison
    H1("5. Comparison")
    P("Table 4 compares the capabilities of PIX2DB with the main families of prior work, as described in the "
      "respective papers. Table structure recognition models [[nassar2022tableformer,smock2022pubtables]] recover "
      "the grid, including spans, but neither type the columns nor resolve spans into records. Page-to-markup models "
      "[[blecher2023nougat,poznanski2025olmocr,auer2024docling]] produce HTML or Markdown for whole pages; their "
      "output keeps the visual structure and, as the HTML baseline in Section 4 shows, loses accuracy once that "
      "structure has to be normalized. Donut-style parsers [[kim2022donut]] emit task-specific JSON fields and have "
      "been applied to receipts, but they do not produce a general relational schema. Chart-to-table models "
      "[[liu2023deplot,masry2023unichart]] cover charts only. OptiSQL [[li2026optisql]] is closest in its use of "
      "SQL, but it generates a query against an existing database for a given question, is evaluated on clean "
      "single-table renderings and does not reconstruct the database.")
    C, X, O = "✓", "✗", "◐"
    table(["Method family", "Typed\nschema", "Multi-table,\nFK", "Spans\nresolved", "Charts", "Photos,\nreceipts",
           "Executable DB"],
          [["Table structure recognition", X, X, X, X, O, X],
           ["Page-to-markup models", X, X, X, X, O, X],
           ["Donut-style parsing", O, X, X, X, C, X],
           ["Chart-to-table models", X, X, "–", C, X, X],
           ["OptiSQL", "–", X, X, X, X, X],
           ["PIX2DB (ours)", C, C, C, C, C, C]],
          [2157, 950, 950, 950, 950, 950, 950],
          "Capability comparison with prior work, as described in the respective papers (◐: partly, or for a subset "
          "of inputs; –: not applicable). Donut-style parsers emit task-specific JSON fields; OptiSQL emits a query "
          "against an existing database.", bold_rows=(5,), head_size=15)
    P("Quantitatively, the strongest alternative in this study is a large general model combined with an HTML "
      "conversion script. It is competitive on flat tables and slightly better on photographed tables from an unseen "
      "source, but it cannot express relations (FK recall 0.00), it loses most of its accuracy on merged cells, "
      "forms and scans, and its type inference leaves formatted numbers as text. PIX2DB reaches higher accuracy with "
      "a model four times smaller, writes outputs half as long and runs about four times faster per image. Its "
      "advantage comes from making the relational decisions part of the learned output, which no prior method in "
      "Table 4 does.")

    # ================================================================== 6. Conclusions
    H1("6. Conclusions")
    P("This study introduced image-to-database reconstruction and PIX2DB, a 2B vision-language model that turns a "
      "document image into an executable SQLite database. Training pairs with exact gold databases were obtained by "
      "rendering samples of real relational databases at six layout levels and by converting existing table and "
      "receipt annotations under the same conventions. With a deterministic verify-and-repair layer, the model "
      "reaches 0.86 table exact match and 0.99 foreign-key recall on rendered tables from unseen databases, cell F1 of "
      "0.81 and 0.96 on held-out PubTabNet and FinTabNet tables and recall of 0.93 on receipt photographs, "
      "outperforming models of the same family with four times more parameters on five of six evaluation sets.")
    P("Three findings follow from the experiments. First, the relational conventions (resolving merged cells, "
      "separating forms from item tables, typing values and declaring foreign keys) are learned reliably by a small "
      "model, whereas general models apply them inconsistently. Second, rendered data teaches these conventions but "
      "not robust reading; a modest amount of converted real data closes most of the gap to real images. Third, on a "
      "source held out from training the remaining weakness is reading text in photographs rather than structure. "
      "Future work will apply the recipe to larger base models, add handwritten and multi-page documents and section "
      "rows, and improve chart reading. The model, data, code and all evaluation outputs are publicly available.")

    # ================================================================== back matter
    BACK("Author Contributions", "M.P.: conceptualization, methodology, software, data curation, investigation, "
         "formal analysis, visualization and writing (original draft, review and editing).")
    BACK("Funding", "This research received no external funding.")
    BACK("Data Availability Statement", "The model is available at https://huggingface.co/musapeker/pix2db-2b, the "
         "dataset with all training and evaluation splits at https://huggingface.co/datasets/musapeker/pix2db-data, "
         "and the code, evaluation outputs and figure scripts at https://github.com/m-peker/pix2db. An interactive "
         "demonstration is available at https://huggingface.co/spaces/musapeker/pix2db.")
    BACK("Acknowledgments", f"A preprint of this manuscript is available on Research Square: {g['PREPRINT']}. The "
         "author used Claude (Anthropic), an AI assistant, for support in software development, experiment "
         "orchestration, data analysis scripts, figure generation and language editing. The research idea, the "
         "experimental design decisions and the interpretation of the results were reviewed and approved by the "
         "author, who takes full responsibility for the content of this article.")
    BACK("Conflicts of Interest", "The author declares no conflict of interest.")

    # ================================================================== appendices (placed after references)
    body = g["BODY"]
    start = len(body)
    H1("Appendix A. Instruction")
    P("All SQL systems receive the image and the following text; PIX2DB was trained with it:")
    P("<i>Convert all data shown in this image into a SQLite database. Output only SQL, in a single sql code block: "
      "1. CREATE TABLE statements: snake_case table and column names; column types INTEGER, REAL or TEXT; PRIMARY KEY "
      "and FOREIGN KEY constraints where the image implies a relationship (for example a document header and its line "
      "items). 2. INSERT statements for every record. Rules: one row per record (repeat the value of a merged cell in "
      "every row it covers); flatten multi-level headers into single column names; store numbers without thousand "
      "separators or currency symbols; write dates as YYYY-MM-DD; use NULL for empty cells; do not store total or "
      "subtotal rows (they are derived); for a chart, create one table with the category column and one column per "
      "data series; do not invent rows or columns.</i>")
    P("The HTML pipeline instead asks for every table and form in the image as HTML table elements, keeping rowspan "
      "and colspan, with each key-value form written as a one-row table, and copying cell text exactly.")
    H1("Appendix B. Repair Layer per Evaluation Set")
    rep = [[clean(c) for c in r] for r in tex_rows("repair.tex")]
    table(["Set", "PIX2DB exec", "PIX2DB F1", "8B exec", "8B F1", "2B exec", "2B F1"], rep,
          [1957, 983, 983, 983, 983, 983, 985],
          "Share of executable outputs and cell F1 before → after the repair layer. For receipts the F1 column shows "
          "cell F1, not the recall used in Table 2.", label="Table A1", size=16)
    H1("Appendix C. Training and Inference Settings")
    table(["Setting", "Value"],
          [["Base model", "Qwen3-VL-2B-Instruct (Apache-2.0)"],
           ["Adapter", "LoRA, r = 64, α = 128, dropout 0.05; q, k, v, o, gate, up and down projections of the language model"],
           ["Vision encoder", "frozen"],
           ["Image budget", "at most 1,310,720 pixels"],
           ["Optimization", "AdamW, learning rate 10<sup>−4</sup>, cosine schedule, 3% warm-up, 1 epoch, batch 4 × accumulation 4, bf16, gradient checkpointing"],
           ["Data", "36,589 examples (Table 1); target = gold dump in visual reading order"],
           ["Hardware and time", "1 × NVIDIA A40 (48 GB); 5.9 h"],
           ["Inference", "vLLM, greedy decoding, at most 3,072 new tokens, same image budget"],
           ["Seed", "42 for data generation, sampling and training"]],
          [2300, 5557], "Training and inference settings.", label="Table A2", left_cols=(0, 1))
    APPENDIX_XML[:] = body[start:]
    del body[start:]


APPENDIX_XML: list[str] = []
