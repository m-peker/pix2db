"""Manuscript text for the FAITH submission (revision 1).

Inline markup: <i>, <b>, <code>, <sup>, <sub>, [[cite keys]], <hl> for text changed in the revision
(yellow when built with FAITH_HIGHLIGHT=1). Revision numbers come from paper/tables_rev (make_rev_tables.py),
first-round numbers from paper/numbers.tex. The first-submission text is kept in manuscript_v1.py.
"""

TITLE = ("PIX2DB: Reconstructing Executable Relational Databases from Document Images with a 2B "
         "Vision-Language Model")
AFFILIATION = ("Ozveri R&amp;D Center, Ozdilek Home Textile Industry and Trade Inc., Osmangazi, Bursa 16150, "
               "Türkiye; e-mail: musa.peker@ozdilek.com.tr")
CORRESPONDING = "Corresponding Author: Musa Peker (musa.peker@ozdilek.com.tr)"
ORCID = "0000-0002-6495-9187"
KEYWORDS = ("Document understanding; Image-to-SQL; Relational schema reconstruction; Synthetic data; "
            "Table extraction; Vision-language models")
ABSTRACT = ""  # set in write(), it needs the revision numbers


def write(g):
    global ABSTRACT
    H1, H2, H3, P, PC, BUL, NUM, BACK = (g[k] for k in ["H1", "H2", "H3", "P", "PC", "BUL", "NUM", "BACK"])
    figure, table, equation, algorithm, N, R, RT = (g[k] for k in ["figure", "table", "equation", "algorithm", "N",
                                                                     "R", "RT"])
    mr, frac, sub, nsum, paren = g["mr"], g["frac"], g["sub"], g["nsum"], g["paren"]
    FIG = g["HERE"] / "fig"

    def r(k):  # revision number, visible placeholder while a run is still pending
        v = R.get(k, "[pending]")
        return v.replace("+", "").replace("-", "−") if k.startswith(("diff_", "ci_", "degci_")) else v

    def PH(t):  # paragraph that is new or rewritten in the revision
        P(f"<hl>{t}</hl>")

    def BULH(items):
        BUL([f"<hl>{x}</hl>" for x in items])

    have_ablation = "synth_synth" in R and "synth_real" in R

    ABSTRACT = (
        "<hl>Much operational data reaches organizations as images: scanned invoices, photographed receipts, "
        "screenshots of spreadsheets and rendered charts. Table extraction tools return a grid or HTML that keeps "
        "the layout but leaves the relational decisions open, so merged cells, a document header and its line "
        "items, and formatted numbers still have to be resolved by hand before the data can be queried.</hl> This "
        "study defines image-to-database reconstruction, in which a model must turn one image into a SQLite dump "
        "whose tables, column types, primary and foreign keys and rows load and can be queried directly. Training "
        "data with exact gold databases is produced by rendering samples of the Spider databases at six layout "
        "levels and by converting PubTabNet, FinTabNet and CORD annotations under the same normalization rules. "
        "<hl>Qwen3-VL-2B, adapted with LoRA on 36,589 image–dump pairs and followed by a deterministic "
        "verify-and-repair layer, is compared with Qwen3-VL models of 2B, 4B and 8B parameters, an 8B "
        "HTML-to-SQLite pipeline, Docling, and the same 2B model fine-tuned to emit HTML.</hl> "
        f"<hl>On rendered documents from unseen databases it reaches {r('synth_ours')} table exact match, and on "
        f"this synthetic test it recovers {r('fkr_ours')} of the gold foreign keys with a precision of "
        f"{r('fkp_ours')}, against {r('synth_q8')}, {r('fkr_q8')} and {r('fkp_q8')} for the 8B model prompted for "
        f"SQL (p &lt; 0.001 for exact match). On held-out tables from the training sources it obtains cell F1 of "
        f"{r('ptn_ours')} on PubTabNet, where the difference to the 8B HTML pipeline is not significant "
        f"(p {r('p_ptn_h8')}), and {r('ftn_ours')} on FinTabNet (p &lt; 0.001). Two independent sources mark the "
        f"limits: on photographed TabRecSet tables the 8B HTML pipeline is better ({r('trs_h8')} against "
        f"{r('trs_ours')}), and on full-page invoices the model transcribes the line items but misses the "
        f"invoice header and its key (cell recall {r('inv_ours')} against {r('inv_q8')}). The 2B model "
        f"fine-tuned for HTML matches the cell accuracy of the SQL model on every set but cannot express keys, "
        f"and three training seeds differ by at most {r('seed_maxsd')} (standard deviation). Relational "
        f"conventions are therefore learned reliably from exact data, whereas reading unfamiliar images and "
        f"transferring document structure to new templates remain open problems.</hl>")

    # ================================================================== 1. Introduction
    H1("1. Introduction")
    PH("Tabular data is often available only as a picture. Suppliers send invoices as scanned PDFs, expense "
       "claims arrive as photographs of receipts, spreadsheets are shared as screenshots and monthly figures "
       "circulate as rendered charts. An accounts-payable clerk who receives such an invoice needs more than its "
       "text: the invoice number, date and supplier have to become one record, every line item has to become a "
       "record that points to it, and amounts such as \"1.250,00 €\" have to become numbers, so that a question "
       "like \"how much did we spend per supplier this quarter\" can be answered by one query. The research "
       "object of the present study is this step: the reconstruction of a relational database from a single "
       "document image.")
    P("Existing work approaches the problem from the layout side. Table structure recognition (TSR) predicts the "
      "grid of a cropped table, from early convolutional detectors [[schreiber2017deepdesrt,paliwal2019tablenet,"
      "prasad2020cascadetabnet]] to image-to-sequence and transformer models trained on large corpora "
      "[[zhong2020pubtabnet,smock2022pubtables,nassar2022tableformer]]. OCR-free document models parse pages into "
      "markup without a separate text recognizer [[kim2022donut,lee2023pix2struct,blecher2023nougat,wei2024got,"
      "poznanski2025olmocr]], and chart models translate plots into linearized tables [[liu2023deplot]]. These "
      "methods are strong at describing how a table <i>looks</i>: TSR models recover row and column spans "
      "accurately, and general vision-language models (VLMs) read printed text well. <hl>Their output, however, "
      "is still a layout, and a layout cannot be queried. An HTML table or a CSV file keeps a two-level header as "
      "two rows of labels, keeps a merged cell as one cell that covers several rows, keeps a key–value block as "
      "free text and has no way to state that one block refers to another. Every number is a string. Before a "
      "single <code>JOIN</code> or <code>SUM</code> can run, someone has to decide which rows a merged value "
      "belongs to, which header row is a group label, whether \"(1,209)\" is a negative number, and which "
      "column links the line items to their header. In practice these decisions are made by hand-written "
      "rules for each document type, and they break when the layout changes.</hl>")
    P("This study addresses the relational step that follows recognition and performs it directly from pixels. "
      "Prompting a general model is not enough. In a pilot study with 150 "
      "rendered images, Qwen3-VL-8B [[bai2025qwen3vl]] produced an executable SQL dump for 93% of the images but a "
      "completely correct table for only 61%; the same model asked for HTML, converted to SQLite by a short script, "
      "reached 46% and failed precisely on merged cells and forms. The errors were rarely misread characters. The "
      "models placed merged values in a single row, invented header tables, omitted foreign keys, or wrote a name "
      "such as <code>O'Brien</code> without escaping, so that one malformed row invalidated an entire statement. The "
      "closest prior work, OptiSQL [[li2026optisql]], generates one SQL query per question from a clean table image "
      "and never reconstructs the database.")
    tf = figure(FIG / "teaser.png", "A rendered document from a test database (a), the two grids a layout "
                "extractor returns for it (b), the SQLite dump written by PIX2DB (c) and a query that runs on the "
                "dump without further processing (d). Blue marks the key and the join that link the header to the "
                "items; red marks what the layout output leaves unresolved.", hl=True)
    PH(f"{tf} makes the difference concrete. The page contains a key–value header that describes one user and a "
       "property table with a two-level header. A layout extractor (b) returns the header as text and the table "
       "as a grid whose first row, \"Details, Details, Figures, Figures\", is a group label rather than data; "
       "nothing in the output says that the properties belong to user 10. The dump (c) makes three decisions "
       "instead. The header becomes its own one-row table with a primary key, the group labels disappear and the "
       "column names are flattened, and the owner column of the item table is declared as a foreign key to that "
       "table. The query in (d), which joins the two tables and aggregates per user, then runs unchanged on the "
       "result. For an invoice the same three decisions separate the invoice record from its line items and let "
       "totals per supplier or per month be computed across many documents, which is what downstream accounting, "
       "auditing or analytics systems require.")
    P("We propose PIX2DB, a 2B-parameter model whose output already contains these decisions. Given an image, it "
      "writes a SQLite dump with <code>CREATE TABLE</code> statements (column types, primary and foreign keys) "
      "followed by <code>INSERT</code> statements for every record. A deterministic verify-and-repair layer then "
      "executes the dump, fixes common syntactic failures and flags suspicious content. The main contributions "
      "are:")
    NUM(["A task definition for image-to-database reconstruction with explicit normalization conventions, and an "
         "evaluation protocol that aligns predicted and gold databases without relying on table or column names"
         "<hl>, extended with schema-level measures (foreign- and primary-key precision, referential integrity, "
         "table and column counts) and with query-execution equivalence on automatically generated queries</hl>.",
         "A data construction method that yields exact gold databases at scale, by rendering samples of real "
         "relational databases at controlled layout difficulty and by converting existing table and receipt "
         "annotations into the same conventions, with every gold dump verified by execution.",
         "<hl>PIX2DB-2b, a LoRA-adapted 2B model with a deterministic repair layer. On rendered documents from "
         "unseen databases it recovers foreign keys almost completely and with few false keys; on real tables "
         "from the training sources it matches or exceeds an 8B model, and on two independent sources it does "
         "not.</hl>",
         "<hl>Controlled experiments that separate the sources of these results: a task-adapted HTML baseline "
         "trained on the same data, synthetic-only and real-only training at matched size, three training seeds, "
         "per-level, per-degradation and per-chart-type analyses, and an ablation of each repair strategy with "
         "an account of the information it removes.</hl>"])
    PH("The rest of the paper is organized as follows. Section 2 reviews related work and summarizes the "
       "capabilities of existing approaches. Section 3 defines the task and describes the data construction, the "
       "model, the repair layer and the evaluation protocol. Section 4 analyzes PIX2DB across layout levels, image "
       "degradations, chart types, schema metrics, training data, repair strategies and training runs. Section 5 "
       "compares it with existing methods on all evaluation sets, including two independent sources. Section 6 "
       "discusses the findings and their limits, and Section 7 concludes.")

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
      "[[nassar2022tableformer]] and the PubTables-1M detector predict structure and take the cell text from the "
      "PDF or from OCR. <hl>The evaluation of this line of work rewards a faithful copy of the visual grid: under "
      "TEDS a reproduced rowspan counts as correct, although a database would need the spanned value in every "
      "row, and a header row is scored as a row of cells whatever its role. The task is therefore defined one "
      "step before the relational decisions, and the absence of types or keys in these models is a matter of "
      "scope rather than a failure.</hl>")
    H2("2.2. OCR-Free Document Models and Charts")
    P("Layout-aware pre-training such as LayoutLM [[xu2020layoutlm]] and LayoutLMv3 [[huang2022layoutlmv3]] "
      "combines OCR tokens with visual features. Donut [[kim2022donut]] and Pix2Struct [[lee2023pix2struct]] showed "
      "that an image-to-sequence model can parse documents without an OCR stage, and Nougat "
      "[[blecher2023nougat]], GOT [[wei2024got]], olmOCR [[poznanski2025olmocr]] and Docling [[auer2024docling]] "
      "convert pages into Markdown, LaTeX or HTML. <hl>Donut comes closest to a record-level output: fine-tuned on "
      "receipts, it emits a JSON object with a fixed set of fields, but the fields are defined per dataset, so "
      "each new document type needs a new schema and new annotations, and relations between objects are not "
      "part of the output. Page-to-markup models are general but inherit the limits of markup described above. "
      "Efficient on-device vision models [[aduvuku2026ondevice]] make small VLMs attractive for this kind of "
      "processing, which motivates the 2B scale used here.</hl> General VLMs such as Qwen3-VL [[bai2025qwen3vl]] "
      "read tables well enough to be the strongest baselines in this study. For charts, DePlot [[liu2023deplot]], "
      "MatCha [[liu2023matcha]] and UniChart [[masry2023unichart]] translate plots into linearized tables, "
      "evaluated on ChartQA [[masry2022chartqa]] and PlotQA [[methani2020plotqa]]. <hl>Their output is a "
      "flat table of strings; none of these models targets a typed relational schema or relations between "
      "tables, and here a chart is treated as one more layout whose target is a typed table.</hl>")
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
      "data with free and exact labels follows a long tradition in text recognition [[gupta2016synthtext]]<hl>, and "
      "synthetic data generation is used more generally to cover cases that are rare or expensive to annotate "
      "[[rahman2025gans]]. Robustness to capture conditions is a recurring concern for vision systems: corruption "
      "benchmarks show that accuracy drops under blur, noise and compression [[hendrycks2019robustness]], and "
      "low-light enhancement can restore detection performance on degraded images [[ramadani2025lumen]]. Section "
      "4.3 tests the corresponding degradations of document scans.</hl>")
    H2("<hl>2.4. Capabilities and Research Gap</hl>")
    PH("Table 1 summarizes the capabilities of the main families of prior work with respect to the six "
       "requirements of image-to-database reconstruction. The assessment is based on the output format and the "
       "evaluation reported in the cited papers, not on new experiments, with one exception: the HTML pipeline "
       "and Docling are also evaluated in Sections 4 and 5. A check mark (✓) means that the capability is "
       "produced by the method and evaluated in its paper. A half circle (◐) means that it is produced for a "
       "subset of inputs or only implicitly, for example fields of a fixed receipt schema. A cross (✗) means that "
       "the output format cannot express the capability, so it could not be obtained without changing the "
       "method. An open circle (○) means that the format could express it but the work does not address it; "
       "this marks a difference in scope, not a limitation of the method.")
    C, X, O, S = "✓", "✗", "◐", "○"
    t_cap = table(["Method family", "Typed\nschema", "Multi-table,\nFK", "Spans\nresolved", "Charts",
                   "Photos,\nreceipts", "Executable\nDB"],
                  [["TSR [[nassar2022tableformer,smock2022pubtables,zhong2020pubtabnet]]", X, X, X, S, O, X],
                   ["Page-to-markup [[blecher2023nougat,poznanski2025olmocr,auer2024docling]]", X, X, X, S, O, X],
                   ["Donut-style parsing [[kim2022donut,park2019cord]]", O, X, S, S, C, X],
                   ["Chart-to-table [[liu2023deplot,liu2023matcha,masry2023unichart]]", X, X, "–", C, S, X],
                   ["Image + question → SQL [[li2026optisql]]", S, S, S, S, S, X],
                   ["PIX2DB (ours)", C, C, C, C, O, C]],
                  [2357, 917, 917, 917, 917, 917, 916],
                  "Capabilities of existing method families for image-to-database reconstruction. ✓ produced and "
                  "evaluated; ◐ partly, for a subset of inputs or implicitly; ✗ not expressible in the output "
                  "format; ○ expressible but outside the scope of the cited work; – not applicable. Typed schema: "
                  "declared numeric and text columns; Multi-table, FK: several tables with declared foreign keys; "
                  "Spans resolved: merged cells expanded into records; Executable DB: the output loads into a "
                  "database without a conversion step.",
                  bold_rows=(5,), head_size=15, hl=True)
    PH("Two observations follow from Table 1. First, no family produces an executable database: TSR and "
       "page-to-markup models stop at the grid, Donut-style parsers at a fixed set of fields, chart models at a "
       "flat table, and OptiSQL produces a query against a database that must already exist. Second, most "
       "missing capabilities are structural rather than a matter of accuracy. HTML and Markdown have no "
       "construct for a foreign key, and a fixed JSON schema has none for an arbitrary table, so better models "
       "of these families would not close the gap; it has to be addressed by changing the output. PIX2DB is "
       "marked ◐ for photographs because Sections 4 and 5 show that it reads receipt photographs well but "
       "photographed tables from an unseen source less well than a larger model. The gap addressed here is "
       "therefore the relational step itself: a single model that writes the typed, keyed and executable "
       "database, and an evaluation that measures that database rather than its layout.")

    # ================================================================== 3. Proposed Method
    H1("3. Proposed Method")
    P("Figure 2 gives an overview. Training pairs of an image and its gold SQLite dump are built from two sources: "
      "rendered samples of real relational databases and converted annotations of real table and receipt images. A "
      "2B VLM is adapted with LoRA to write the dump, and at inference time its output passes through a "
      "verify-and-repair layer before it is loaded into SQLite.")
    figure(FIG / "method.png", "Overview of PIX2DB. (a) Two sources of training pairs and LoRA fine-tuning; "
           "(b) inference with the verify-and-repair layer.")
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
         "<b>L6 chart</b>: bar, horizontal bar, line and pie charts with one to three series<hl>, drawn with "
         "matplotlib from the scene values. Value labels are printed on 60% of the charts; the other 40% show only "
         "axes and gridlines.</hl>"])
    P("Synthetic receipts use narrow monospaced layouts with three item-line formats, modifiers such as \"less "
      "sugar\", subtotal, tax and payment lines, and are photographed 85% of the time. Two invariants keep the gold "
      "exact. Every displayed string maps back to the gold value without loss: formatting adds separators or "
      "symbols but never rounds or truncates. Because rendering may reorder rows and columns, for example to group "
      "merged cells, the gold scene is reordered in the same way, so the target dump follows the reading order of the "
      "image. <hl>For a chart the gold is the table the chart was drawn from, not a reading of the chart, so it "
      "is exact whether or not labels are printed.</hl> Splits are made by database: the 146 Spider training "
      "databases feed training, the 20 development databases validation, and the 40 databases that appear only in "
      "Spider's test set form the synthetic test.")
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
    H3("<hl>3.2.3. Origin of keys and relations</hl>")
    PH("Keys are part of the target only where the source provides them or where the document structure "
       "determines them unambiguously; they are never inferred from values. In the synthetic scenes both kinds "
       "of key come from the Spider schema. A primary key is declared when the Spider table declares a "
       "single-column primary key and the sampled rows keep it unique and non-null; composite keys are not "
       "declared. A foreign key is declared only in parent–child scenes, and only between the two columns that "
       "the Spider schema itself declares as a foreign key; the scene sampler selects the parent row through that "
       "relation. The relational part of the synthetic gold is therefore taken from the original database "
       "design, not introduced during preprocessing.")
    PH("PubTabNet, FinTabNet, CORD, TabRecSet and the synthetic receipts contain one table per image, and their "
       "gold databases declare no primary or foreign key. On these sets the evaluation measures cells, row "
       "segmentation, column types and query results, but not relations, and no key-related number in this paper "
       "is computed on them. A model that declares a key on these sets is not penalized by the cell metrics, and "
       "its keys are not counted as correct. The only real-looking set with relations is the invoice set of "
       "Section 4.1, built for this revision. There the invoice number is printed once in the header and is the "
       "natural identifier of the document, so the gold makes it the primary key of an <i>invoice</i> table and "
       "adds it as a foreign key column to every line item. This relation is introduced by us from the document "
       "structure and is stated as such; it is the only place where the gold contains a key that the source "
       "annotation does not.")
    H3("3.2.4. Execution check and dataset statistics")
    P("Every gold dump, synthetic or converted, is executed and scored against itself; any score below 1.0 indicates "
      "a defect in the data. The check found composite keys declared as primary keys, numbers stored as text in "
      "Spider, identifiers that start with a digit or are SQL keywords (these are now quoted), empty strings in "
      "numeric columns, and one header-deduplication collision in a converted table, which was removed. "
      "<hl>Table 2 lists every split, the number of images available and the number used in each role. The "
      "first submission reported the pool of 24,000 synthetic images in its dataset table and the 14,000 drawn "
      "from it in the text; both are now shown side by side.</hl>")
    t_data = table(["Split", "Source", "Images", "Used for\ntraining", "Tables\nper image", "Rows", "Columns",
                    "With FK"],
                   [["<i>Training</i>", "", "", "", "", "", "", ""],
                    ["Synthetic L1–L6", "Spider train DBs (146)", "24,000", "14,000", "1.38", "5.4", "3.7", "29%"],
                    ["Synthetic receipts", "rendered", "3,000", "3,000", "1.00", "7.1", "3.5", "0%"],
                    ["PubTabNet", "train split, converted", "9,999", "9,999", "1.00", "9.9", "5.0", "0%"],
                    ["FinTabNet", "train split, converted", "8,000", "8,000", "1.00", "9.5", "4.2", "0%"],
                    ["CORD", "train split, converted", "795", "795 × 2", "1.00", "2.6", "3.0", "0%"],
                    ["Synthetic L1–L6, extra", "Spider train DBs (146)", "9,589", "ablation only", "1.38", "5.4",
                     "3.7", "29%"],
                    ["<i>Validation</i>", "", "", "", "", "", "", ""],
                    ["Synthetic L1–L6", "Spider dev DBs (20)", "600", "–", "1.30", "6.0", "3.6", "22%"],
                    ["<i>Test: training sources</i>", "", "", "", "", "", "", ""],
                    ["Synthetic L1–L6", "Spider test-only DBs (40)", "900", "–", "1.32", "5.4", "3.4", "24%"],
                    ["Synthetic charts", "Spider test-only DBs (40)", "300", "–", "1.00", "6.2", "2.2", "0%"],
                    ["Degraded L5 (9 variants)", "Spider test-only DBs (40)", "9 × 150", "–", "1.55", "4.9", "3.6",
                     "41%"],
                    ["Synthetic receipts", "rendered", "150", "–", "1.00", "6.8", "3.5", "0%"],
                    ["PubTabNet", "validation split", "150", "–", "1.00", "9.4", "4.2", "0%"],
                    ["FinTabNet", "validation split", "150", "–", "1.00", "8.5", "4.6", "0%"],
                    ["CORD", "test split", "60", "–", "1.00", "3.5", "3.0", "0%"],
                    ["<i>Test: independent sources</i>", "", "", "", "", "", "", ""],
                    ["TabRecSet", "photographed tables", "150", "–", "1.00", "6.7", "3.8", "0%"],
                    ["Invoices", "full-page invoices", "490", "–", "2.00", "2.5", "7.0", "100%"]],
                   [1700, 1900, 760, 900, 700, 600, 700, 597],
                   "Dataset splits. Rows and columns are averages over all tables, including the one-row header tables "
                   "of document scenes; \"With FK\" is the share of images whose gold database declares a foreign key. "
                   "The v2 training mixture is the \"Used for training\" column (36,589 examples). The extra "
                   "synthetic images are used only by the synthetic-only model of Section 4.5.",
                   size=15, head_size=14, hl=True)
    H2("3.3. Model and Training")
    P("PIX2DB-2b is Qwen3-VL-2B-Instruct [[bai2025qwen3vl]] adapted with low-rank adaptation (LoRA) "
      "[[hu2022lora,dettmers2023qlora]]. For every linear projection <i>W</i> of the language model (attention "
      "query, key, value and output, and the MLP gate, up and down projections), the frozen weight is complemented "
      "by a trainable low-rank update, as shown in Eq. (1):")
    equation(mr("W") + mr("′", True) + mr("=") + mr("W") + mr("+") + frac(mr("α"), mr("r")) + mr("B") + mr("A"))
    PC("where <i>B</i> ∈ ℝ<sup>d×r</sup> and <i>A</i> ∈ ℝ<sup>r×k</sup> with rank <i>r</i> = 64 and scaling "
       "<i>α</i> = 128; <i>B</i> is initialized to zero so that training starts from the base model, and the "
       "vision encoder is not adapted. The model receives the image <i>I</i> and a fixed instruction <i>x</i> "
       "and is trained to generate the gold dump <i>y</i>. The loss is the token-level cross-entropy "
       "over the answer tokens only, as given in Eq. (2):")
    equation(mr("ℒ") + paren(mr("θ")) + mr("=") + mr("−") + frac(mr("1"), mr("|Y|")) +
             nsum(mr("t∈Y"), mr("log ", True) + sub(mr("p"), mr("θ")) +
                  paren(sub(mr("y"), mr("t")) + mr(" | ") + sub(mr("y"), mr("<t")) + mr(", I, x"))))
    PC("where <i>Y</i> is the set of positions of the SQL answer; image and instruction tokens and padding are "
       "masked out. <hl>The instruction, used verbatim for PIX2DB and for every SQL baseline, is:</hl>")
    PH("<i>Convert all data shown in this image into a SQLite database. Output only SQL, in a single sql code "
       "block: 1. CREATE TABLE statements: snake_case table and column names; column types INTEGER, REAL or TEXT; "
       "PRIMARY KEY and FOREIGN KEY constraints where the image implies a relationship (for example a document "
       "header and its line items). 2. INSERT statements for every record. Rules: one row per record (repeat the "
       "value of a merged cell in every row it covers); flatten multi-level headers into single column names; "
       "store numbers without thousand separators or currency symbols; write dates as YYYY-MM-DD; use NULL for "
       "empty cells; do not store total or subtotal rows (they are derived); for a chart, create one table with "
       "the category column and one column per data series; do not invent rows or columns.</i>")
    PH("The training mixture is the \"Used for training\" column of Table 2. Each image is resized by the Qwen3-VL "
       "processor so that its area is at most 1,310,720 pixels (about 1,280 visual tokens of 32 × 32 pixels), "
       "keeping the aspect ratio; no other preprocessing or augmentation is applied at training time, since the "
       "scan effects of L5 are part of the rendered data. Sequences of image, instruction and answer are capped "
       "at 4,096 tokens. Table 3 lists the full configuration. "
       "After training, the update of Eq. (1) is merged into the base weights, so inference has the cost of the "
       "base model.")
    t_set = table(["Setting", "Value"],
                  [["Base model", "Qwen3-VL-2B-Instruct (Apache-2.0)"],
                   ["Adapter", "LoRA, r = 64, α = 128, dropout 0.05; q, k, v, o, gate, up and down projections of "
                    "all language-model layers (about 70 M trainable parameters)"],
                   ["Vision encoder and projector", "frozen"],
                   ["Image preprocessing", "aspect-preserving resize to at most 1,310,720 pixels; no augmentation"],
                   ["Optimizer", "AdamW (β₁ = 0.9, β₂ = 0.999, ε = 10<sup>−8</sup>, weight decay 0), learning "
                    "rate 10<sup>−4</sup>, 3% linear warm-up, cosine decay to 0, gradient clipping at 1.0"],
                   ["Batch and length", "4 images per step × 4 accumulation steps = 16; maximum 4,096 tokens"],
                   ["Schedule", "1 epoch = 2,287 optimizer steps; the final checkpoint is used"],
                   ["Precision and memory", "bf16, gradient checkpointing"],
                   ["Hardware and time", "1 × NVIDIA A40 (48 GB); 5.9 h"],
                   ["Inference", "vLLM, greedy decoding, at most 3,072 new tokens, same image budget for all "
                    "systems"],
                   ["Seeds", "42 for data generation, sampling and training; 1 and 2 for the additional runs of "
                    "Section 4.7"]],
                  [2300, 5557], "Training and inference settings (formerly Appendix C).", left_cols=(0, 1), hl=True)
    PH("Three design choices deserve a justification. <i>LoRA instead of full fine-tuning.</i> The task "
       "changes what the model writes, not what it sees, and the base model already reads printed text and "
       "writes SQL; a low-rank update of the language model is sufficient to teach output conventions and keeps "
       "the general abilities of the base model, as LoRA updates have been found to forget less than full "
       "fine-tuning [[biderman2024lora]]. It also fits a 2B model with 4,096-token sequences and high-resolution "
       "images on one 48 GB GPU. A rank of 64 on all projections is a common setting for instruction tuning of "
       "models of this size [[dettmers2023qlora]]; it was not tuned. <i>Frozen vision encoder.</i> Keeping the "
       "encoder fixed follows the usual practice for adapting VLMs to new output formats "
       "[[liu2023llava]] and avoids overfitting the visual features to the 146 rendered databases. The cost of "
       "this choice is visible in Section 5: the remaining errors on unseen photographs are reading errors, which "
       "an adapted encoder might reduce. <i>One epoch.</i> The training examples are cheap to generate, so more "
       "data was preferred over repeated passes. The training loss falls mostly in the first tenth of the epoch "
       "and changes little after the first third (Section 4.7), and the three seeds end within a narrow range, "
       "which indicates that a longer schedule would mainly add cost. These choices were fixed before the "
       "evaluation and were not selected on the test sets.")
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
      "[[pourreza2023dinsql]] in text-to-SQL, but it operates after generation and needs no additional model call. "
      "<hl>The five strategies (truncation salvage, apostrophe escaping, identifier quoting and renaming, "
      "primary-key dropping and row-by-row insertion) can be switched off individually, which Section 4.6 uses "
      "to measure each one.</hl>")
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
       "numeric or textual. <hl>Because these measures concern cells, five schema measures are added. <i>FK "
       "precision</i> is the share of declared foreign keys that connect two matched tables related in the gold "
       "through the aligned columns; <i>PK precision</i> is defined in the same way for primary keys. "
       "<i>Referential integrity</i> is the share of child rows whose foreign-key value exists in the parent "
       "table of the predicted database. <i>Table count</i> and <i>column count</i> record whether the predicted "
       "database has as many tables as the gold, and each matched table as many columns. Finally, "
       "<i>query-execution equivalence</i> tests the database as a whole. For each gold database a fixed set of "
       "queries is generated from its schema: the row count of every table, the sum, minimum and maximum of every "
       "numeric column, the number of distinct values of every text column, and for every foreign key the number "
       "of rows of the join. The queries are translated to the predicted database through the table and column "
       "alignment, executed on both, and counted as equivalent when the results agree (numbers within the "
       "tolerance below, multiplied by the row count for sums). The reported value is the pooled share of "
       "equivalent queries. It needs no hand-written questions and penalizes errors that cell F1 hides, such as "
       "a dropped row that changes a count or a number stored as text that cannot be summed.</hl> Two cases "
       "are relaxed. Values of charts drawn without value labels match within the tolerance of Eq. (5):")
    equation(mr("|") + mr("v̂") + mr("−") + mr("v") + mr("|") + mr("≤") + mr("τ") + mr(",   ") + mr("τ") + mr("=") +
             mr("0.04") + mr("·") + sub(mr("max", True), mr("i")) + mr("|") + sub(mr("v"), mr("i")) + mr("|"))
    PC("<hl>where the maximum runs over the values of the chart, so that a bar or slice may be off by 4% of the "
       "largest value, roughly the resolution at which a value can be read against gridlines. Values of labeled "
       "charts must match exactly after normalization. Receipts and invoices are scored by recall, because a "
       "correct database may legitimately contain an extra table for totals or payment that the gold does not "
       "store.</hl>")

    # ================================================================== 4. Experiments
    H1("<hl>4. Experimental Analysis</hl>")
    H2("4.1. Experimental Setup")
    P("All experiments were run on a single NVIDIA A40 (48 GB) with PyTorch 2.8, Hugging Face Transformers and PEFT "
      "for training, and vLLM [[kwon2023vllm]] for inference. <hl>PIX2DB is compared with six systems. Qwen3-VL-2B, "
      "4B and 8B-Instruct receive the instruction of Section 3.3 without fine-tuning. In the 8B HTML pipeline, "
      "Qwen3-VL-8B outputs HTML tables that keep row and column spans, with each key–value form written as a "
      "one-row table, and a script loads them with <code>pandas.read_html</code>, which expands spans, into "
      "SQLite. Docling [[auer2024docling]] represents dedicated document converters: TableFormer "
      "[[nassar2022tableformer]] in its accurate mode with full-page EasyOCR and cell matching, followed by the "
      "same loader. Finally, a task-adapted baseline is trained with exactly the recipe and data of PIX2DB but "
      "with the gold rendered as plain HTML tables instead of SQL; it shows what fine-tuning achieves when the "
      "target is a layout format.</hl> All SQL outputs go through the same repair layer. Decoding is greedy with "
      "at most 3,072 new tokens and the same image budget for all systems.")
    PH("The evaluation sets are listed in Table 2. Besides the synthetic test (150 images per level), held-out "
       "splits of the real training sources are used: 150 PubTabNet and 150 FinTabNet validation tables, 60 CORD "
       "test receipts with at least two items and 150 synthetic receipts. These images are unseen, but their "
       "style is familiar from training. Three sets were added for this revision. <i>Charts</i> are 300 further "
       "charts from the test databases, 98 bar, 76 horizontal bar, 67 line and 59 pie charts, 198 of them with "
       "value labels. <i>Degraded scans</i> re-render the 150 L5 test scenes once without degradation and once "
       "with each of eight degradations at its strongest training setting. <i>Invoices</i> are 490 full-page "
       "invoices from a public invoice dataset [[katanaml2023invoices]] (MIT license), produced by a generator "
       "unrelated to ours, with a different layout, fonts and page size; the dataset annotates the header fields "
       "and the line items, from which the two-table gold of Section 3.2.3 is built. Its annotation omits the "
       "item number, the unit of measure and the summary table, so recall is reported.")
    P("To measure transfer to photographs, TabRecSet-150 was built from TabRecSet [[yang2023tabrecset,"
      "tabrecsetdata]] (CC BY 4.0), which was not used for training; because it has been public since 2022 it may "
      "have been part of the base model's pre-training. Only English original images are taken (not the generated "
      "three-line and no-line variants, which repeat the same tables), one table per image, cropped by its cell "
      "polygons and with at least 60% non-empty cells. TabRecSet does not mark header rows, so the first grid row "
      "is used as header; 64% of the inspected tables pass the conversion rules. Its annotators wrote illegible "
      "characters as <code>#</code>, and these are kept in the gold (94 of 4,199 cells, in 26 tables); removing "
      "them from scoring changes cell F1 by less than 0.01 for every system and leaves the ranking unchanged. "
      "Some images contain handwriting and three cells contain Chinese characters; neither was filtered. 95% "
      "confidence intervals come from 2,000 bootstrap resamples of evaluation items, and <i>p</i>-values from a "
      "one-sided paired bootstrap against each competitor<hl>; differences whose paired interval contains zero "
      "are called not significant. Unless stated otherwise, numbers refer to the seed-42 model after repair; "
      "Section 4.7 reports the spread over three seeds.</hl>")

    # ---- 4.2 levels
    H2("<hl>4.2. Performance across Layout Levels</hl>")
    hdr, rows = RT("levels")
    t_lv = table(hdr, rows, [2457, 900, 900, 900, 900, 900, 900],
                 "Table exact match / cell F1 per synthetic level (150 test images each, unseen databases). The "
                 "2B HTML model is the task-adapted baseline trained on the same data with an HTML target.",
                 size=15, head_size=15, hl=True)
    PH(f"{t_lv} reports both metrics per level, replacing the bar chart of the first submission. Cell F1 is high "
       f"for all VLMs on L1 and L2, so the differences lie in exact match, that is, in whether a table is "
       f"complete and correctly segmented. <i>Clean and styled tables (L1, L2).</i> PIX2DB reaches "
       f"{r('lv1_ours')} and {r('lv2_ours')}, close to the 8B model ({r('lv1_q8')}, {r('lv2_q8')}) and to the 8B "
       f"HTML pipeline ({r('lv1_h8')}, {r('lv2_h8')}). Styling does not hurt: humanized headers, separators and "
       f"currency signs are normalized as reliably as raw values. The failures at these levels are near misses; "
       f"{r('lvfail1_le2')} of the L1 and {r('lvfail2_le2')} of the L2 failures differ from the gold in one or "
       f"two cells. <i>Hierarchical tables (L3).</i> Merged cells and two-level headers separate the systems. "
       f"PIX2DB keeps {r('lv3_ours')} exact match, the 8B SQL model falls to {r('lv3_q8')} and the HTML pipeline "
       f"to {r('lv3_h8')}, although its cell F1 ({r('lv3_h8_f1')}) shows that most text is still read. The "
       f"remaining PIX2DB failures are more often structural: {r('lvfail3_rows')} of them have a wrong number of "
       f"rows, against {r('lvfail1_rows')} at L1. <i>Documents (L4).</i> The key–value header is the easiest "
       f"layout for PIX2DB ({r('lv4_ours')}), because it is short and its conventions are regular, and among "
       f"the hardest for the HTML pipeline ({r('lv4_h8')}), whose loader has no notion of a form above a table. "
       f"<i>Scans (L5).</i> Exact match drops only from {r('lv4_ours')} to {r('lv5_ours')}; Section 4.3 breaks "
       f"this down by degradation. <i>Charts (L6)</i> are the weakest level for PIX2DB ({r('lv6_ours')}) and for "
       f"the 8B model prompted for SQL ({r('lv6_q8')}); only for the 8B HTML pipeline are hierarchical tables and "
       f"scans harder. Section 4.4 analyzes the charts.")
    PH(f"Two conclusions follow. First, PIX2DB is not particularly effective under one condition only: from L1 "
       f"to L5 its exact match stays between {r('lv1_ours')} and {r('lv4_ours')}, while the 8B HTML pipeline "
       f"ranges from {r('lv1_h8')} to {r('lv5_h8')}. Second, the task-adapted 2B HTML model matches PIX2DB on "
       f"every level; its output is converted by the same loader that fails for the 8B pipeline. The loader is "
       f"therefore not the problem when the HTML is written in a regular, expanded form. What the 8B pipeline "
       f"lacks is training on the conventions, not a better format, a point taken up in Section 5.")

    # ---- 4.3 degradations
    H2("<hl>4.3. Effect of Individual Degradations (L5)</hl>")
    hdr, rows = RT("degrade")
    t_dg = table(hdr, rows, [2257, 620, 620, 620, 620, 620, 620, 620, 620, 640],
                 "Table exact match on the 150 L5 test scenes rendered without degradation (Clean) and with one "
                 "degradation at a time: rotation 2.5°, uneven lighting, Gaussian noise σ = 9, Gaussian blur "
                 "radius 0.9, contrast 0.8, grayscale, JPEG quality 45, and all effects as in training (All). "
                 "Docling is reported as cell F1 because its exact match is near zero.",
                 size=15, head_size=14, hl=True)
    PH(f"The L5 level mixes several degradations, so its result does not show which of them matter. {t_dg} "
       f"isolates them. For PIX2DB the clean scenes reach {r('deg_clean_ours')} exact match and no single "
       f"degradation lowers this by more than three points; the largest drops come from uneven lighting and "
       f"noise ({r('deg_lighting_ours')} and {r('deg_noise_ours')}; paired differences "
       f"{r('degci_lighting')} and {r('degci_noise')}), and blur and rotation have smaller effects. The 8B "
       f"model and the task-adapted HTML model behave in the same way. Docling, whose OCR stage reads "
       f"characters from pixels, is sensitive in a way the VLMs are not: blur lowers its cell F1 from "
       f"{r('deg_clean_dl')} to {r('deg_blur_dl')} and rotation to {r('deg_rotation_dl')}. These results should "
       f"not be read as robustness to real scans. The degradations are applied at the strength used for training "
       f"data, the rendered text is large and sharp to begin with, and the rotation never exceeds 2.5°. They "
       f"show that the model is not disturbed by moderate, known degradations; real scanning artefacts such as "
       f"folds, stamps, shadows and perspective are tested only indirectly through the receipt photographs and "
       f"TabRecSet in Section 5.")

    # ---- 4.4 charts
    H2("<hl>4.4. Charts by Type and Labeling (L6)</hl>")
    hdr, rows = RT("charts")
    t_ch = table(hdr, rows, [1897, 600, 620, 600, 600, 720, 720, 700, 700, 700],
                 f"Results on 300 test charts ({r('nch_bar')} bar, {r('nch_barh')} horizontal bar, {r('nch_line')} "
                 f"line, {r('nch_pie')} pie; {r('nch_lab')} with value labels). Columns 2–5: table exact match by "
                 f"chart type; then exact match and cell F1 for labeled and unlabeled charts.",
                 size=15, head_size=14, hl=True)
    PH(f"{t_ch} breaks charts down by type and labeling. The gold of every chart is the table it was drawn "
       f"from. For a labeled chart a value matches only if it equals the printed label after normalization; for "
       f"an unlabeled chart the model has to estimate the value from the position of the mark, and Eq. (5) "
       f"accepts it within 4% of the largest value of the chart. A table counts as exact when every cell "
       f"matches under these rules. Pie charts are the easiest type for PIX2DB ({r('ch_pie_ours')}), because "
       f"they have one series and few categories, and vertical bar charts the hardest ({r('ch_bar_ours')}); "
       f"there the 8B model is clearly better ({r('ch_bar_q8')}). Labeling matters less than expected: exact "
       f"match is {r('ch_lab_ours')} with labels and {r('ch_unlab_ours')} without, and cell F1 is "
       f"{r('ch_labf1_ours')} and {r('ch_unlabf1_ours')}. The tolerance makes estimation feasible, and the "
       f"remaining errors on labeled charts show that reading the numbers is not the main problem. On the L6 "
       f"level of the synthetic test, {r('lvfail6_rows')} of the failed charts have a wrong number of rows, "
       f"that is, a missing or an extra category, against {r('lvfail1_rows')} of the failed L1 tables, and only "
       f"{r('lvfail6_le2')} are off by one or two cells; the difficulty lies as much in assigning marks to "
       f"categories and series as in reading values. Over all charts the 8B model is ahead ({r('chart_q8')} "
       f"against {r('chart_ours')}), "
       f"but the difference is not significant (paired interval {r('ci_chart_q8')}). Charts are thus the one "
       f"synthetic layout where training on the conventions brings no advantage over a larger untuned model.")

    # ---- 4.5 schema and data
    H2("<hl>4.5. Relational Structure and Training Data</hl>")
    hdr, rows = RT("schema")
    t_sc = table(hdr, rows, [2257, 700, 700, 700, 700, 700, 700, 700, 700],
                 "Schema and query measures on the synthetic test (900 images; foreign-key measures on the "
                 "images whose gold declares a foreign key). Keys cannot be expressed in HTML, so key precision "
                 "and referential integrity are undefined (–) for the HTML-based systems.",
                 size=15, head_size=14, hl=True)
    PH(f"{t_sc} answers whether the relational part of the output is correct, beyond the cells. PIX2DB declares "
       f"{r('fkr_ours')} of the gold foreign keys, and of the keys it declares {r('nfk_ours')} are correct "
       f"(precision {r('fkp_ours')}). The 8B model declares about as many keys but more wrong ones "
       f"({r('nfk_q8')} correct, precision {r('fkp_q8')}) and finds {r('fkr_q8')} of the gold keys; the 4B and "
       f"2B models find only a quarter ({r('fkr_q4')} and {r('fkr_q2')}). Referential "
       f"integrity is {r('ri_ours')}, so the declared keys are also satisfied by the inserted rows. Primary keys "
       f"show the largest difference: {r('npk_ours')} of the PIX2DB primary keys agree with the gold (precision "
       f"{r('pkp_ours')}), against {r('npk_q8')} for the 8B model ({r('pkp_q8')}), which declares far more "
       f"primary keys than the gold contains. The number of tables is right in every case, the number of columns in "
       f"{r('cc_ours')} of the tables, and {r('qa_ours')} of the generated queries return the gold result. These "
       f"numbers are measured on rendered scenes from unseen databases, but on the layouts and conventions of the "
       f"training data; the invoice results of Section 5.3 show how much of this transfers to an unfamiliar "
       f"document type.")
    hdr, rows = RT("data_ablation")
    t_ab = table(hdr, rows, [1215, 745, 830, 775, 680, 745, 775, 745, 680, 735],
                 "Effect of the training data. All models use the recipe of Table 3 and differ only in the data. "
                 "Synthetic: exact match; PubTabNet, FinTabNet, TabRecSet: cell F1; CORD, receipts, invoices: "
                 "recall; charts: exact match; FK recall on the synthetic test.",
                 size=15, head_size=13, hl=True)
    have_synth = "synth_synth" in R
    PH(f"The first submission compared a model trained on 24,000 synthetic images with the mixed model "
       f"trained on 36,589 examples, so the amount of data and its kind changed together. {t_ab} adds two "
       f"controls trained for this revision: a synthetic-only model with 36,589 examples, the same number as "
       f"the mixture, and a model trained only on the 19,589 converted real examples.")
    if have_synth:
        PH(f"With the size fixed, synthetic-only training still transfers poorly: PubTabNet F1 "
           f"{r('ptn_synth')}, FinTabNet {r('ftn_synth')}, CORD recall {r('cord_synth')} and TabRecSet "
           f"{r('trs_synth')}, against {r('ptn_ours')}, {r('ftn_ours')}, {r('cord_ours')} and {r('trs_ours')} for "
           f"the mixture. The real-table scores are the same as for the 24,000-image model of the first "
           f"submission, so the additional 12,589 synthetic examples bring nothing on real tables, and the gap of "
           f"the first submission is caused by the kind of data, not its amount. CORD is the exception "
           f"({r('cord_synth')}), because the synthetic part includes the rendered receipts, which are close to the "
           f"CORD layout.")
    else:
        PH("[pending: synthetic-only run]")
    PH(f"The real-only model is the more informative control. On the real table sets it is as good as the "
       f"mixture: {r('ptn_real')} on PubTabNet, {r('ftn_real')} on FinTabNet and {r('trs_real')} on TabRecSet, "
       f"against {r('ptn_ours')}, {r('ftn_ours')} and {r('trs_ours')}. The synthetic data does not make the model "
       f"read real tables better. What it adds is everything the real annotations do not contain. The real-only "
       f"model reaches {r('synth_real')} exact match on the synthetic test and declares no foreign key at all "
       f"(FK recall {r('fkr_real')}), because no real example has a merged-cell group, a form or a relation. It "
       f"also falls behind on the document types that the mixture covers only synthetically: receipts "
       f"{r('rcpt_real')} against {r('rcpt_ours')}, invoices {r('inv_real')} against {r('inv_ours')}, and charts "
       f"{r('chart_real')} against {r('chart_ours')}. The two sources therefore teach different things: the real "
       f"data teaches reading, the synthetic data teaches the relational structure, and the mixture keeps both "
       f"without a measurable cost on either side.")
    PH(f"The failures of the synthetic-only model on real tables were rarely layout errors. In 82 of 150 "
       f"PubTabNet outputs of the first synthetic model the SQL did not execute at all (28 after repair), mostly "
       f"because composite values such as <code>9 (8)</code> or <code>85.0 ± 10.8</code> were written as bare "
       f"numbers, a format that never occurs in Spider; in other cases the model looped on a "
       f"<code>CREATE TABLE</code> statement it could not finish. The real data contributes the variety of "
       f"cell contents and typography of real documents; the synthetic data contributes the relational "
       f"structure. Neither alone is sufficient.")

    # ---- 4.6 repair
    H2("<hl>4.6. Contribution and Cost of the Repair Layer</hl>")
    hdr, rows = RT("repair_sets")
    t_rs = table(hdr, rows, [1957, 983, 983, 983, 983, 983, 985],
                 "Share of executable outputs and cell F1 before → after the repair layer, per evaluation set "
                 "(formerly Appendix B). For receipts and invoices the F1 column shows cell F1, not recall.",
                 size=16, hl=True)
    hdr, rows = RT("repair_strategies")
    t_rst = table(hdr, rows, [2557, 883, 883, 883, 883, 883, 885],
                  f"Ablation of the individual repair strategies, pooled over the synthetic test, PubTabNet, "
                  f"FinTabNet, CORD and synthetic receipts (1,410 outputs per model): share of executable outputs "
                  f"and cell F1.", size=16, hl=True)
    hdr, rows = RT("repair_loss")
    t_rl = table(hdr, rows, [1357, 800, 900, 1000, 900, 1000, 1100, 800],
                 "What the repair layer changes, over the same 1,410 outputs per model. Rescued: outputs that do "
                 "not execute without repair; their F1 and precision after repair. Rows dropped: rows that still "
                 "fail after row-by-row insertion. PKs dropped: primary-key constraints removed because later rows "
                 "violate them.", size=15, head_size=14, hl=True)
    PH(f"{t_rs} reports the layer per set. It raises the share of executable outputs on every set where outputs "
       f"fail, most on PubTabNet and TabRecSet, but cell F1 changes by at most three points for PIX2DB. "
       f"{t_rst} isolates the strategies. For PIX2DB, row-by-row insertion alone recovers almost all failures "
       f"(execution {r('rs_none_exec')} → {r('rs_only row_fallback_exec')}), and primary-key dropping adds the "
       f"rest of the F1 gain; apostrophe escaping and identifier rewriting matter only for the untuned 2B model, "
       f"which writes names such as <code>O'Brien</code> and free-text column names. Removing any single strategy "
       f"from the full layer lowers PIX2DB execution by less than half a point (at worst "
       f"{r('rs_full_exec')} → {r('rs_-row_fallback_exec')}), so the strategies overlap and none is critical "
       f"alone.")
    PH(f"Execution is not correctness, so {t_rl} accounts for what the layer adds and removes. Of the 1,410 "
       f"PIX2DB outputs, {r('loss_resc_pix2db-2b-v2')} do not execute without repair. After repair they reach "
       f"cell F1 {r('loss_rescf1_pix2db-2b-v2')} and precision {r('loss_rescp_pix2db-2b-v2')}, so they are mostly "
       f"correct databases that a single malformed row had invalidated, not noise that the layer turns into "
       f"data. The information removed is small and reported: {r('loss_rows_pix2db-2b-v2')} gold rows are "
       f"dropped because they still fail, and {r('loss_pk_pix2db-2b-v2')} primary-key constraints are removed "
       f"because the model wrote duplicate key values. Dropping a key keeps every row but loses the uniqueness "
       f"guarantee, and each case is returned as a warning so that a user can decide. Statements that execute "
       f"are never modified, so the layer cannot lower the F1 of a correct output; for the untuned 2B model, "
       f"whose rescued outputs reach only F1 {r('loss_rescf1_Qwen3-VL-2B-Instruct')}, it mainly turns failures "
       f"into partial databases. The repair layer is therefore a safety net for a well-trained model, not a "
       f"substitute for training: with all strategies the base 2B model reaches a pooled F1 of 0.64, far "
       f"below PIX2DB without any repair ({r('rs_none_f1')}).")

    # ---- 4.7 seeds
    H2("<hl>4.7. Variability across Training Runs</hl>")
    hdr, rows = RT("seeds")
    t_sd = table(hdr, rows, [2057, 1200, 1200, 1200, 2200],
                 "Primary metric per evaluation set for three training runs that differ only in the random seed "
                 "(data order, LoRA initialization and dropout); mean and standard deviation over the runs.",
                 size=16, hl=True)
    PH(f"All other numbers come from one training run, so {t_sd} repeats the training with seeds 1 and 2. The "
       f"runs agree closely: the largest standard deviation over {r('nseeds')} runs is {r('seed_maxsd')} "
       f"({r('seed_maxsd_set')}), and on {r('seed_nsmall')} of the eight sets it is below 0.01. "
       f"Training variance is thus an order of magnitude smaller than the differences to the baselines discussed "
       f"in Section 5, and smaller than the bootstrap intervals over test items. FK recall is {r('seed_fk')} "
       f"over the runs. The TabRecSet result in particular is not an unlucky run ({r('seed_trs')}). The training "
       f"loss, logged every 10 steps, falls mostly in the first tenth of the epoch and changes little after "
       f"the first third; for seed 1 the mean loss is {r('loss_s1_q4')} in the fourth tenth of the epoch and "
       f"{r('loss_s1_q10')} in the last, for seed 2 {r('loss_s2_q4')} and {r('loss_s2_q10')}.")

    # ---- 4.8 cost
    H2("4.8. Column Types and Cost")
    P(f"Stored types are almost always right for every SQL system (type accuracy 0.98–0.99, {t_sc}); the 8B HTML "
      f"pipeline reaches 0.89 because pandas infers types from formatted strings, so \"$1,250\" stays text, and "
      f"Docling 0.77. PIX2DB writes the shortest outputs ({N['tokours']} tokens on average, against "
      f"{N['tokhtml']} for the 8B HTML pipeline<hl> and 304 for the task-adapted HTML model, whose expanded "
      f"tables repeat merged values</hl>), which together with its size makes it the fastest system: 0.09 s per "
      f"image amortized over a vLLM batch on one A40. <hl>Training one model takes 5.9 h on one A40; the "
      f"revision experiments, five trainings and all evaluations, used about 60 GPU-hours.</hl>")

    # ================================================================== 5. Comparison
    H1("<hl>5. Comparison with Existing Methods</hl>")
    H2("<hl>5.1. Results on All Evaluation Sets</hl>")
    lbl_main = f"Table {g['TABNO'][0] + 1}"  # introduced before the table so the heading is not left alone
    PH(f"{lbl_main}, moved here from Section 4, compares all systems on all sets. The comparison is limited to "
       f"systems that can be run on the same images and scored by the same protocol: three sizes of the base "
       f"model family, the strongest prompting pipeline found in the pilot study, a dedicated document "
       f"converter, and the task-adapted baseline. It does not establish superiority over the state of the art "
       f"in table recognition, which is measured with other metrics on other test sets, and the results should "
       f"be read as a comparison of approaches to the relational task under one protocol.")
    PH(f"<i>Where PIX2DB is better.</i> On the synthetic test it leads the 8B SQL model by "
       f"{r('diff_synth_q8')} in exact match (0.856 against 0.754 before rounding) and the 8B HTML pipeline by "
       f"{r('diff_synth_h8')}, and its foreign-key "
       f"recall ({r('fkr_ours')}) has no counterpart among the baselines. On FinTabNet, CORD and the synthetic "
       f"receipts it is ahead of every untuned system by at least 8 points (p &lt; 0.001). Docling is far behind "
       f"on every set except FinTabNet ({r('ftn_dl')}): its table detector was trained on cleanly typeset "
       f"pages, and on crops, receipts and photographs it often finds no table at all. <i>Where it is not "
       f"better.</i> On PubTabNet the 8B HTML pipeline is behind by only {r('diff_ptn_h8')} and the difference "
       f"is not significant; flat scientific tables are exactly the case for which HTML suffices. On charts the 8B "
       f"model is slightly ahead, as discussed in Section 4.4. On the two independent sources PIX2DB loses, "
       f"which Sections 5.3 and 5.4 analyze.")
    hdr, rows = RT("main")
    t_main = table(hdr, rows, [1300, 740, 780, 770, 720, 740, 770, 730, 720, 587],
                   "Comparison on all evaluation sets, with 95% bootstrap intervals. Synthetic and charts: table "
                   "exact match; PubTabNet, FinTabNet and TabRecSet: cell F1; CORD, synthetic receipts and "
                   "invoices: cell recall; FK recall on the synthetic test images that contain a foreign key. "
                   "TabRecSet and invoices are independent sources. Best value per column in bold.",
                   footer=f"Paired bootstrap against PIX2DB (one-sided). The base 2B model and Docling are behind "
                          f"on every set (p &lt; 0.001). The 8B and 4B SQL models are behind on every set "
                          f"(p &lt; 0.001) except invoices, where they are ahead (p &lt; 0.001), and charts, where "
                          f"the differences are not significant. The 8B HTML pipeline is behind on every set "
                          f"(p ≤ 0.009) except PubTabNet (p {r('p_ptn_h8')}) and TabRecSet, where it is ahead "
                          f"(difference {r('diff_trs_h8')}, interval {r('ci_trs_h8')}). No difference to the "
                          f"task-adapted 2B HTML model is significant on any set.",
                   size=13, head_size=13, hl=True)
    hdr, rows = RT("query")
    t_q = table(hdr, rows, [1650, 740, 800, 780, 720, 760, 800, 760, 847],
                "Query-execution equivalence on all sets: pooled share of the automatically generated queries "
                "(Section 3.5) whose result on the predicted database equals the result on the gold database.",
                size=15, head_size=14, hl=True)
    PH(f"{t_q} repeats the comparison with query-execution equivalence, which tests whether the database "
       f"answers aggregate questions correctly. The ranking is the same as for the cell metrics, but the gaps "
       f"are larger where cell metrics are lenient. On FinTabNet the 8B HTML pipeline has cell F1 "
       f"{r('ftn_h8')} but query equivalence of only {r('qe_ftn_h8')}, against {r('qe_ftn_ours')} for PIX2DB: "
       f"most cells are read, but numbers formatted with separators or parentheses stay text, so their sums and "
       f"maxima are wrong. On the receipts the gap is {r('qe_rcpt_ours')} against {r('qe_rcpt_h8')} for the "
       f"same reason. A database is only as useful as the queries it answers, so this measure supports the "
       f"choice of a typed target more directly than cell F1 does.")
    H2("<hl>5.2. Task-Adapted Baseline: Does the SQL Target Matter?</hl>")
    PH(f"The task-adapted 2B HTML model separates two explanations for the gains above: training on the "
       f"conventions, or writing SQL. Trained on the same data with an HTML target, it matches PIX2DB on every "
       f"set: synthetic exact match {r('synth_html2b')} against {r('synth_ours')}, PubTabNet F1 "
       f"{r('ptn_html2b')}, TabRecSet {r('trs_html2b')}, and no difference in {t_main} is significant. Most of "
       f"the improvement over the untuned models therefore comes from fine-tuning on data that encodes the "
       f"conventions, and an HTML target trained in this way is a strong option when only the cells are needed. "
       f"The SQL target adds what HTML cannot express: keys and relations (FK recall {r('fkr_ours')} against "
       f"0), declared column types instead of types guessed by a loader, and a single output that loads "
       f"without a conversion step. Its outputs are also shorter (195 against 304 tokens), because merged values "
       f"are not repeated in markup. We regard this as the accurate statement of the contribution: the "
       f"relational decisions can be learned by a small model from exact data, and the SQL target is what makes "
       f"them explicit and checkable.")
    H2("<hl>5.3. Independent Multi-Table Documents: Invoices</hl>")
    fi = figure(FIG / "invoice_case.png", "An invoice from the independent invoice set (a) with the output of "
                "PIX2DB (b) and of Qwen3-VL-8B prompted for SQL (c). PIX2DB reads the item table correctly but "
                "does not treat the header fields as a record; the 8B model writes a header table with a primary "
                "key, links the items to it and adds a summary table that the gold does not store.", hl=True)
    PH(f"The invoices are the strongest test of the relational claim, because they combine a header and line "
       f"items as in L4 but come from a different generator. Here PIX2DB fails, and the failure is "
       f"instructive ({fi}). Its cell recall is {r('inv_rec_ours')} and its FK recall {r('inv_fk_ours')}, against "
       f"{r('inv_rec_q8')} and {r('inv_fk_q8')} for the 8B model and {r('inv_rec_q4')} and {r('inv_fk_q4')} for "
       f"the 4B model. On average it writes {r('inv_nt_ours')} tables per invoice: it transcribes the item table, "
       f"usually without error, and omits the header. The untuned models, which have never seen our layouts, "
       f"recognize an invoice as a document with a header and write the relation spontaneously. The trained "
       f"model has learned to recognize the key–value block of L4, a compact box of \"LABEL - value\" pairs "
       f"directly above the table, and does not generalize this to a header spread over the page with labels "
       f"such as \"Seller:\" and \"Client:\" above multi-line addresses. Fine-tuning on a narrow set of document "
       f"layouts has thus replaced a general but inconsistent ability of the base model with a precise but "
       f"narrow one. The models trained with seeds 1 and 2 behave in the same way "
       f"(recall {r('inv_rec_seed1')} and {r('inv_rec_seed2')}, FK recall {r('inv_fk_seed1')} and "
       f"{r('inv_fk_seed2')}), and so does the task-adapted HTML model. More varied document templates in the training data, or keeping "
       f"part of the base model's behavior through mixing in general instruction data, are the obvious remedies; "
       f"we leave them to future work and report the result as a limitation of the present model.")
    H2("<hl>5.4. Independent Photographs: TabRecSet</hl>")
    fe = figure(FIG / "errors_tabrecset.png", f"Outcome categories on TabRecSet-150. The "
                f"thin orange segment is the key–value category ({N['errourskeyvalue']}, {N['errEightbhtmlkeyvalue']} "
                f"and {N['errEightbsqlkeyvalue']} tables from top to bottom); each row sums to 150.", 0.62)
    P(f"TabRecSet-150 is the other set on which PIX2DB loses ({N['oursunseentabrecset']} against "
      f"{N['Eightbhtmlunseentabrecset']}<hl>; paired difference {r('diff_trs_h8')}, interval {r('ci_trs_h8')}"
      f"</hl>). Each prediction was assigned to one category ({fe}): F1 of at least "
      f"0.9; usable output with the right number of rows but wrong cell contents; a wrong number of rows; a "
      f"two-column key–value table; or no usable output. Key–value layouts, for which the first-row-as-header gold "
      f"is questionable, account for only {N['nkv']} tables and do not explain the gap. The largest bucket for all "
      f"systems is cell content ({N['errourscell']} for PIX2DB, {N['errEightbhtmlcell']} for the HTML pipeline): the "
      f"rows are found but text in photographed, skewed or low-resolution tables is misread. PIX2DB also segments "
      f"rows wrongly more often ({N['erroursrow']} against {N['errEightbhtmlrow']}). Both differences concern "
      f"reading the image rather than organizing its content, and that is where the larger model has the "
      f"advantage.")
    PH(f"A cell F1 of 0.52 also means that about half of the cells of an unfamiliar photographed table are "
       f"wrong or missing, which is far from usable without review; the best system reaches only "
       f"{r('trs_h8')}. Generalization to unfamiliar document images is therefore the main open problem, for "
       f"PIX2DB and for the baselines alike. The held-out PubTabNet, FinTabNet and CORD splits share their "
       f"sources with the training data and overstate performance on new documents; TabRecSet and the invoices "
       f"are the better estimate, and on both the model is clearly weaker than on the familiar sources. The "
       f"three seeds reproduce the TabRecSet result within 0.01 (Section 4.7), so it is a property of the "
       f"training data and model size, not of a single run.")

    # ================================================================== 6. Discussion
    H1("<hl>6. Discussion</hl>")
    H2("<hl>6.1. Organizing Is Learned, Reading Is Not</hl>")
    PH("The experiments separate two abilities that an image-to-database system needs. The first is organizing: "
       "deciding which values form a record, how a merged cell expands, which header row is a label, which "
       "column is a key and how two blocks relate. These decisions are few and regular. General VLMs know them "
       "but apply them inconsistently; the 8B model declares three quarters of the foreign keys, a fifth of its "
       "declared keys are wrong, and it resolves merged cells about two times in three. After training on a few tens of "
       "thousands of exact examples, a 2B model applies them almost every time (Section 4.5), with an HTML or "
       "a SQL target alike (Section 5.2), and across all synthetic layout levels except charts. The second "
       "ability is reading: recovering the characters of an unfamiliar photograph and the marks of a chart. "
       "Here training on our data helps little. The synthetic-only model read rendered text well and real "
       "text poorly, the real data fixed the familiar sources but not TabRecSet, and on unfamiliar photographs "
       "the larger model remains ahead (Sections 4.5 and 5.4). The real-only control shows the same split from "
       "the other side: it reads the real tables as well as the mixture, but it declares no key and organizes "
       "no layout it was not shown.")
    PH("This division has practical consequences. Organizing can be taught with synthetic data whose gold is "
       "free and exact, so a new convention, such as a different date format or a new kind of relation, costs "
       "only a change to the renderer. Reading has to be learned from real images of the target kind, and its "
       "cost grows with the variety of documents. The invoice results add a warning: organizing generalizes "
       "within the layouts it was trained on, not to every document with the same logical structure. The "
       "synthetic layouts must therefore be varied enough to cover the documents that will be processed, and "
       "the real data must cover the capture conditions. For image-to-database reconstruction in general, the "
       "results suggest building a system from a strong reader and a trained organizer, with a typed, "
       "executable target that makes the organizing decisions visible and testable, and a verification layer "
       "that reports what it changes.")
    H2("6.2. Validity of the Evaluation")
    PH("The metric ignores names, so a schema with unhelpful column names scores as well as a good one; naming "
       "quality is not measured. Query-execution equivalence uses generated aggregate queries rather than "
       "natural questions; it tests counts, sums, extremes, distinct values and joins, but not filters on "
       "specific values or more complex SQL. Foreign-key and primary-key measures are available only on the "
       "synthetic test and the invoices, because the other sources contain one table per image without keys "
       "(Section 3.2.3). TabRecSet's missing header annotation forces a header assumption that is wrong for "
       "some tables, although the error analysis shows that it affects few. The invoice gold omits three "
       "columns and the summary table, which is why recall is used; it cannot penalize extra tables. Bootstrap "
       "intervals reflect the sampling of test items, and the three seeds cover training variance; other "
       "sources of variance, such as a different base model, are not covered.")
    H2("<hl>6.3. Demonstrated, Partially Supported and Untested Capabilities</hl>")
    t_scope = table(["Capability", "Status", "Evidence"],
                    [["Merged cells, multi-level headers, styled tables", "demonstrated",
                      f"synthetic L1–L3, PubTabNet, FinTabNet ({t_lv}, {t_main})"],
                     ["Header–items documents with FK", "demonstrated on our layouts; not transferred",
                      "L4 (FK recall 0.99); invoices (FK recall 0.01, Section 5.3)"],
                     ["Receipt photographs", "demonstrated", f"CORD, synthetic receipts ({t_main})"],
                     ["Photographed tables from new sources", "partially", "TabRecSet F1 0.52 (Section 5.4)"],
                     ["Robustness to scanning", "partially",
                      "moderate synthetic degradations only (Section 4.3)"],
                     ["Charts", "partially", "exact match 0.71; not better than 8B (Section 4.4)"],
                     ["Handwriting", "untested", "a few TabRecSet images only"],
                     ["Multi-page and long tables (> 30 rows)", "untested", "excluded from all data"],
                     ["Section rows inside table bodies", "untested", "excluded from all data"],
                     ["Non-English documents", "untested", "three Chinese cells in TabRecSet"]],
                    [2857, 2200, 2800], "Scope of the evidence in this study.", left_cols=(0, 1, 2), size=16,
                    hl=True)
    PH(f"{t_scope} separates what the experiments show from what they do not. Handwriting, multi-page "
       "tables, tables longer than 30 rows and tables with section rows in the body were excluded from both "
       "training and evaluation, so the behavior of the model on them is unknown. The data is English apart "
       "from a few TabRecSet cells. The synthetic degradations of L5 are moderate and should not be taken as "
       "evidence of robustness to real scanned documents; the photographed receipts and tables are the only "
       "real capture conditions tested. Receipts and invoices may contain personal data; the released data uses "
       "public datasets whose images were collected and anonymized by their authors, and the invoice set "
       "contains generated names. Extraction errors are likely to look plausible, so the warnings reported by "
       "the repair layer should be shown to users rather than discarded.")

    # ================================================================== 7. Conclusions
    H1("<hl>7. Conclusions</hl>")
    PH("This study defined image-to-database reconstruction, the task of turning a document image into an "
       "executable relational database with typed columns, keys and relations, and presented PIX2DB, a "
       "LoRA-adapted 2B vision-language model with a deterministic verify-and-repair layer. Training pairs with "
       "exact gold databases were obtained by rendering parts of the Spider databases and by converting "
       "existing table and receipt annotations under one set of conventions, and the evaluation was extended "
       "from cells to keys, referential integrity and query results.")
    PH(f"Three findings stand out. First, the relational conventions are learnable: on rendered documents from "
       f"unseen databases the model declares {r('fkr_ours')} of the foreign keys with precision {r('fkp_ours')}, "
       f"resolves merged cells and headers consistently across layout levels, and these results are stable "
       f"across training seeds. Second, the gain comes from training on exact data rather than from the SQL "
       f"format: the same model trained to emit HTML reads cells equally well, and SQL adds the keys, types and "
       f"direct executability. Third, synthetic data teaches the structure but not the reading of real images, "
       f"and real data the reverse; both are needed. The study also documents where the approach does not yet "
       f"work: on photographed tables from an unseen source and on invoices from an unfamiliar template, a "
       f"larger untuned model is better, and the learned document structure did not transfer. Future work "
       f"should therefore diversify the document templates, add real images of the target capture conditions, "
       f"test larger base models with the same recipe and extend the data to handwriting, multi-page and long "
       f"tables, section rows and other languages. The model, data, code and all evaluation outputs are "
       f"publicly available.")

    # ================================================================== back matter
    BACK("Author Contributions", "M.P.: conceptualization, methodology, software, data curation, investigation, "
         "formal analysis, visualization and writing (original draft, review and editing).")
    BACK("Funding", "This research received no external funding.")
    BACK("Data Availability Statement", "The model is available at https://huggingface.co/musapeker/pix2db-2b, the "
         "dataset with all training and evaluation splits at https://huggingface.co/datasets/musapeker/pix2db-data, "
         "and the code, evaluation outputs and figure scripts at https://github.com/m-peker/pix2db. An interactive "
         "demonstration is available at https://huggingface.co/spaces/musapeker/pix2db.<hl> The models, outputs "
         "and scores of the revision experiments are released with the code.</hl>")
    BACK("Acknowledgments", f"A preprint of this manuscript is available on Research Square: {g['PREPRINT']}.")
    BACK("Conflicts of Interest", "The author declares no conflict of interest.")


APPENDIX_XML: list[str] = []
