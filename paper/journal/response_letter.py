"""Point-by-point response letter (.docx) built from paper/template/FAITH_Response_template.docx.

Numbers come from paper/tables_rev/numbers.json (make_rev_tables.py). Section and table numbers refer to the
revised manuscript built by build_docx.py. Usage: python paper/journal/response_letter.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
PAPER = HERE.parent
TEMPLATE = PAPER / "template" / "FAITH_Response_template.docx"
OUT = HERE / "pix2db_FAITH_response_to_reviewers.docx"
R = json.loads((PAPER / "tables_rev" / "numbers.json").read_text(encoding="utf-8"))


def r(k):
    v = R.get(k, "[pending]")
    return v.lstrip("+").replace("-", "−") if k.startswith(("diff_", "ci_", "degci_")) else v


FONT = '<w:rFonts w:ascii="Garamond" w:hAnsi="Garamond"/>'


def runs(text: str, extra: str = "") -> str:
    out, stack = [], []
    for tok in re.split(r"(</?(?:i|b|g)>)", text):
        if not tok:
            continue
        m = re.fullmatch(r"<(/?)(i|b|g)>", tok)
        if m:
            (stack.remove if m.group(1) else stack.append)(m.group(2))
            continue
        rpr = FONT + extra
        if "b" in stack:
            rpr += "<w:b/><w:bCs/>"
        if "i" in stack:
            rpr += "<w:i/><w:iCs/>"
        if "g" in stack:
            rpr += '<w:color w:val="008000"/>'
        rpr += '<w:sz w:val="22"/><w:szCs w:val="22"/>'
        out.append(f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{html.escape(tok, quote=False)}</w:t></w:r>')
    return "".join(out)


def para(text="", page_break=False, after=None, ind=None):
    ppr = "<w:pageBreakBefore/>" if page_break else ""
    if after is not None:
        ppr += f'<w:spacing w:after="{after}"/>'
    if ind:
        ppr += f'<w:ind w:left="{ind}"/>'
    return f'<w:p><w:pPr>{ppr}<w:jc w:val="both"/></w:pPr>{runs(text)}</w:p>'


BODY: list[str] = []


def P(t="", **kw):
    BODY.append(para(t, **kw))


def concern(who: str, n: int, comment: str, response: list[str], first=False):
    P(f"<g><b>{who}, Concern # {n}:</b></g> <i>{comment}</i>", page_break=first)
    P(f"<b>Author response:</b> {response[0]}")
    for x in response[1:]:
        P(x)
    P()


# ------------------------------------------------------------------ cover
TITLE = ("PIX2DB: Reconstructing Executable Relational Databases from Document Images with a 2B "
         "Vision-Language Model")
P("<b>To:</b> Editor, Journal of Future Artificial Intelligence and Technologies (J.FAITH)")
P("<b>Re:</b> Response to reviewers")
P(f"<b>Manuscript:</b> “{TITLE}”")
P()
P("Dear Editor,")
P()
P("Thank you for allowing a revision of our manuscript, with an opportunity to address the reviewers’ comments. "
  "We are grateful to both reviewers for careful and constructive reports.")
P("We are uploading (a) our point-by-point response to the comments (below) (response to reviewers), (b) an "
  "updated manuscript with yellow highlighting indicating changes (Revised manuscript), and (c) a clean updated "
  "manuscript without highlights (Main Manuscript). Both manuscripts are editable Microsoft Word files.")
P("The revision rests on new experiments rather than on rewording alone. We trained five additional models "
  "(the same 2B model with an HTML target as a task-adapted baseline, a synthetic-only model of the same size as "
  "the mixed model, a real-only model, and two further seeds), added Docling as a dedicated document converter, "
  "built three new evaluation sets (490 independent full-page invoices with a two-table gold database, 300 charts "
  "annotated by type and labeling, and the L5 scenes rendered with each degradation separately), and added "
  "schema-level and query-execution metrics. Several results are unfavourable to our model, in particular on the "
  "independent invoices, and we report them as such; the claims of the paper have been narrowed accordingly. "
  "Section and table numbers below refer to the revised manuscript.")
P()
P("Best regards,")
P("Musa Peker", after=0)
P()

# ------------------------------------------------------------------ Reviewer 1 (Reviewer A)
R1 = "Reviewer#1"
concern(R1, 1, "The practical motivation in the Introduction needs to be strengthened. Explain more clearly why "
        "conventional outputs such as extracted tables, HTML, or CSV are insufficient ... Figure 1 should also be "
        "discussed more meaningfully ... Connecting this example to a realistic document-processing scenario would "
        "make the motivation more convincing.",
        ["Thank you for this suggestion. The Introduction now opens with an accounts-payable scenario: an invoice "
         "whose number, date and supplier must become one record, whose line items must point to that record, and "
         "whose amounts must become numbers before a question such as “spend per supplier this quarter” can be "
         "answered by one query. The second paragraph explains concretely why HTML or CSV is insufficient: a "
         "two-level header stays two rows of labels, a merged cell stays one cell, a key–value block stays free "
         "text, there is no construct for a relation between blocks, and every number is a string, so these "
         "decisions are left to hand-written, document-specific rules.",
         "Figure 1 was redrawn with four panels: (a) the input page, (b) the two grids a layout extractor returns "
         "for it, with the unresolved points marked, (c) the SQLite dump written by PIX2DB, and (d) a join query "
         "that runs on the dump without further processing. A new paragraph walks through the three decisions the "
         "dump makes (separating the key–value header into its own keyed table, flattening the group labels, "
         "declaring the owner column as a foreign key) and explains what they enable for invoices in accounting, "
         "auditing or analytics (Section 1)."])
concern(R1, 2, "The Related Work section should provide a more critical comparison ... Table 4, currently in "
        "Section 5, would be more appropriate in Section 2 ... Include the corresponding references and clarify the "
        "criteria used for the capability indicators (✓, ✗, and ◐). Distinguish between capabilities that are "
        "genuinely unsupported and those that were simply outside the scope of previous studies.",
        ["We agree and have restructured accordingly. Each subsection of Section 2 now ends with a critical "
         "assessment: TSR evaluation (TEDS) rewards a faithful copy of the grid, so missing types and keys are a "
         "matter of scope; Donut-style parsers produce records but with a schema fixed per dataset and without "
         "relations; chart models produce flat string tables.",
         "The capability table is now Table 1 in the new Section 2.4 “Capabilities and Research Gap”, with the "
         "references of each method family in its first column. The criteria are defined in the text and in the "
         "caption, and we introduced a fourth symbol to make the requested distinction: ✓ produced and evaluated; "
         "◐ partly, for a subset of inputs or implicitly; ✗ not expressible in the output format (genuinely "
         "unsupported); ○ expressible but outside the scope of the cited work. A following paragraph derives the "
         "research gap from the table: no family produces an executable database, and most missing capabilities "
         "are structural (HTML has no construct for a foreign key), so they cannot be closed by more accurate "
         "models of the same family. We also changed our own row: PIX2DB is now marked ◐ for "
         "photographs, because the new experiments show weaker reading of unfamiliar photographed tables."])
concern(R1, 3, "The methodology and experimental configuration require further clarification to improve "
        "reproducibility ... justify important design choices such as the LoRA configuration, freezing the vision "
        "encoder, and using only one training epoch. Appendix A ... and Appendix C ... should be integrated into the "
        "relevant main sections.",
        ["Done. The instruction (former Appendix A) is now quoted verbatim in Section 3.3, and the settings table "
         "(former Appendix C) is Table 3 in the same section, extended with the full optimizer configuration "
         "(AdamW β₁ = 0.9, β₂ = 0.999, ε = 10⁻⁸, weight decay 0, warm-up, cosine decay, gradient clipping), the "
         "number of trainable parameters (69.7 M), image preprocessing (aspect-preserving resize to at most "
         "1,310,720 pixels, no augmentation), sequence length, checkpoint selection (the final checkpoint after "
         "one epoch) and the seeds. Both appendices have been removed.",
         "A new paragraph in Section 3.3 justifies the three design choices. LoRA: the task changes the output "
         "conventions rather than the visual input, LoRA updates are known to forget less of the base model, and "
         "the configuration fits one 48 GB GPU; the rank was not tuned. Frozen encoder: this follows common "
         "practice for adapting VLMs to new output formats and avoids overfitting the visual features to 146 "
         "rendered databases; we also state its likely cost, since the remaining errors on unseen photographs are "
         "reading errors. One epoch: data is cheap to generate, the training loss changes little after the first "
         "third of the epoch (seed 1: "
         f"{r('loss_s1_q4')} in the fourth tenth, {r('loss_s1_q10')} in the last), and the three seeds end within "
         "a narrow range. We state that these choices were fixed before evaluation and not selected on test "
         "data."])
concern(R1, 4, "The dataset construction and distribution require clarification. In particular, the training "
        "data quantities reported in Section 3.3 do not appear consistent with those presented in Table 1 ...",
        ["Thank you for spotting this. The inconsistency came from reporting the pool of 24,000 synthetic images in "
         "the dataset table and the 14,000 images drawn from it for the v2 mixture in the text. The new Table 2 "
         "lists, for every split, its source, the number of images available and the number used for training, "
         "grouped into training, validation, test on the training sources and test on independent sources. The "
         "“Used for training” column sums to the 36,589 examples of the mixture (14,000 synthetic, 3,000 "
         "synthetic receipts, 9,999 PubTabNet, 8,000 FinTabNet, 795 CORD receipts seen twice). The synthetic and "
         "converted real sources are separated explicitly, the new evaluation sets are included, and all "
         "statistics are recomputed with one definition stated in the caption. The 600 validation images were "
         "not used for model selection, which is now stated as well."])
concern(R1, 5, "Section 4 should provide a more detailed analysis of the proposed method across the six synthetic "
        "layout levels (L1–L6) ...",
        [f"We replaced the bar chart with Table 4, which reports table exact match and cell F1 per level for six "
         f"systems, and added Section 4.2, which discusses each level. In short: on clean and styled tables PIX2DB "
         f"reaches {r('lv1_ours')} and {r('lv2_ours')} exact match and its failures are near misses "
         f"({r('lvfail1_le2')} and {r('lvfail2_le2')} differ in one or two cells); on hierarchical tables it keeps "
         f"{r('lv3_ours')} while the 8B SQL model falls to {r('lv3_q8')} and the HTML pipeline to "
         f"{r('lv3_h8')}, and its remaining failures are more often structural ({r('lvfail3_rows')} with a wrong "
         f"row count); documents are its easiest level ({r('lv4_ours')}); scans cost little ({r('lv5_ours')}); "
         f"charts are the weakest level for every system ({r('lv6_ours')}). From L1 to L5 its exact match stays "
         f"between {r('lv1_ours')} and {r('lv4_ours')}, whereas the 8B HTML pipeline ranges from {r('lv1_h8')} to "
         f"{r('lv5_h8')}, so the performance is consistent across document characteristics except charts."])
concern(R1, 6, "The analysis of L5 and L6 requires particular attention. For L5, discuss the effects of individual "
        "image degradations ... For L6, report performance separately for different chart types and distinguish "
        "charts with and without explicit numerical labels ... clarify how ground-truth values are established and "
        "how predictions are evaluated when the model must infer values from visual elements.",
        [f"For L5 we rendered the 150 L5 test scenes once without degradation and once with each of eight "
         f"degradations (rotation, uneven lighting, noise, blur, contrast, grayscale, JPEG, and all combined) "
         f"(Section 4.3, Table 5). No single degradation lowers PIX2DB by more than three points of exact match "
         f"(clean {r('deg_clean_ours')}; lighting {r('deg_lighting_ours')}, noise {r('deg_noise_ours')}), and the "
         f"8B and task-adapted models behave the same way; Docling, by contrast, loses most of its accuracy under "
         f"blur (cell F1 {r('deg_clean_dl')} → {r('deg_blur_dl')}). We explicitly caution that these moderate "
         f"synthetic degradations are not evidence of robustness to real scans.",
         f"For L6 we generated 300 further test charts annotated by type and labeling (Section 4.4, Table 6). Pie "
         f"charts are easiest ({r('ch_pie_ours')}) and vertical bar charts hardest ({r('ch_bar_ours')}, where the "
         f"8B model reaches {r('ch_bar_q8')}). Labeled and unlabeled charts differ little ({r('ch_lab_ours')} vs "
         f"{r('ch_unlab_ours')} exact match), and the failure profile shows that assigning marks to categories and "
         f"series is as hard as estimating values. Regarding the ground truth: every chart is drawn from a table "
         f"of the scene, and that table is the gold, so the gold is exact regardless of labeling (Section 3.2.1). "
         f"Values of labeled charts must match exactly; values of unlabeled charts are accepted within 4% of the "
         f"largest value of the chart, Eq. (5), which corresponds roughly to the reading resolution against "
         f"gridlines (Section 3.5)."])
concern(R1, 7, "The ablation study should better isolate the contributions of the individual components. Appendix "
        "B ... should be incorporated into the main experimental discussion ... explain whether repair improves the "
        "semantic correctness and completeness ... Report potential information loss, including discarded records "
        "and removed primary key constraints, and evaluate the individual repair strategies where feasible.",
        [f"The repair layer now has its own Section 4.6 with three tables. Table 9 is the former Appendix B, "
         f"extended to all eight sets. Table 10 evaluates the five strategies individually, each alone and the "
         f"full layer without each one. For PIX2DB, row-by-row insertion alone raises execution from "
         f"{r('rs_none_exec')} to {r('rs_only row_fallback_exec')}, primary-key dropping contributes most of the "
         f"remaining F1 gain, and apostrophe escaping and identifier rewriting matter only for the untuned 2B "
         f"model.",
         f"Table 11 accounts for semantic correctness and information loss. Of 1,410 PIX2DB outputs, "
         f"{r('loss_resc_pix2db-2b-v2')} do not execute without repair; after repair they reach cell F1 "
         f"{r('loss_rescf1_pix2db-2b-v2')} and precision {r('loss_rescp_pix2db-2b-v2')}, so the layer recovers "
         f"mostly correct databases rather than producing noise. The layer drops {r('loss_rows_pix2db-2b-v2')} "
         f"gold rows and removes {r('loss_pk_pix2db-2b-v2')} primary-key constraints, all reported as warnings. "
         f"Statements that execute are never modified, so the layer cannot reduce the F1 of a correct output. The "
         f"training-data ablation was also extended (see Concern #11 and Reviewer#2, Concern #1)."])
concern(R1, 8, "Clarify how the ground-truth relational schemas are constructed from the different data sources, "
        "particularly PubTabNet, FinTabNet, and CORD ... distinguish relationships explicitly available in the "
        "original data from those introduced during preprocessing.",
        ["This is an important point, and the new Section 3.2.3 “Origin of keys and relations” addresses it. In "
         "short: (i) in the synthetic scenes, primary and foreign keys are taken from the Spider schema; a primary "
         "key is declared only where Spider declares a single-column key that stays unique in the sample, and a "
         "foreign key only between the two columns that Spider itself declares as related. They are not inferred "
         "from values. (ii) PubTabNet, FinTabNet, CORD, TabRecSet and the synthetic receipts contain one table "
         "per image, and their gold databases declare no keys at all; no key-related number in the paper is "
         "computed on them. (iii) The only gold relation introduced by us is in the new invoice set, where the "
         "invoice number printed in the header is made the primary key and added to every line item; this is "
         "stated explicitly. Consequently, the reported foreign-key performance reflects structure present in "
         "the original database design rather than assumptions made during preparation, and Section 6.2 notes "
         "that key metrics are available only on the synthetic test and the invoices."])
concern(R1, 9, "The quantitative comparison currently presented in Table 2 should be moved to Section 5 ... discuss "
        "the results on TabRecSet ... Avoid broad state-of-the-art superiority claims ... More directly relevant "
        "methods should be included where comparable experimental evaluation is feasible.",
        [f"The comparison table is now Table 13 in Section 5 “Comparison with Existing Methods”, extended to "
         f"eight sets and two further systems: Docling (TableFormer with OCR) as a dedicated document converter, "
         f"and a task-adapted baseline (the same 2B model trained on the same data with an HTML target). Section "
         f"5.1 discusses separately where PIX2DB is better and where it is not, and states that the comparison "
         f"does not establish superiority over the state of the art in table recognition; we removed the "
         f"corresponding claims from the Abstract, contributions and Conclusions. Section 5.4 discusses "
         f"TabRecSet in detail: the 8B HTML pipeline is ahead by {r('diff_trs_h8')} (interval {r('ci_trs_h8')}), "
         f"the error analysis attributes the gap to reading photographed text, and an F1 of 0.52 is described as "
         f"far from usable without review. A new Section 5.3 reports an independent multi-table set (invoices) "
         f"on which PIX2DB is clearly worse than the 8B model, with a figure showing a typical case."])
concern(R1, 10, "The generalization claims need to be more carefully supported ... The relatively low TabRecSet "
        "F1-score (0.52) suggests that generalization to unfamiliar document images remains challenging ... "
        "acknowledge that all results come from a single training run. Multiple training seeds would provide "
        "stronger evidence of experimental stability.",
        [f"We agree. Section 5.4 now states that the held-out PubTabNet, FinTabNet and CORD splits share their "
         f"sources with the training data and overstate performance on new documents, that TabRecSet and the new "
         f"invoice set are the better estimate of generalization, and that on both the model is clearly weaker. "
         f"Generalization to unfamiliar images is named as the main open problem in Sections 5.4, 6.1 and 7.",
         f"We trained two further models with seeds 1 and 2 (Section 4.7, Table 12). The largest standard "
         f"deviation over the {r('nseeds')} runs is {r('seed_maxsd')} ({r('seed_maxsd_set')}), an order of "
         f"magnitude below the differences to the baselines, and TabRecSet is reproduced within 0.01 "
         f"({r('seed_trs')}), so the low score is a property of the data and model, not of one run."])
concern(R1, 11, "The Discussion section should provide a stronger synthesis of the experimental findings ...",
        ["Thank you; we followed this suggestion closely. The new Section 6.1 “Organizing Is Learned, Reading Is "
         "Not” synthesizes the findings around the observation the reviewer describes: relational organization "
         "(records, merged cells, header roles, keys) is learned from a few tens of thousands of exact examples, "
         "with an SQL or an HTML target alike, whereas reading unfamiliar photographs is not improved by our "
         "data. The controlled data ablation now supports the second part of the observation (synthetic-only "
         "training at the same size still transfers poorly; real-only training reads real tables but learns no "
         "relations), and the invoice result adds a qualification: learned organization generalizes within the "
         "trained layouts but not to every document with the same logical structure. The second paragraph draws "
         "implications for image-to-database systems: conventions can be taught cheaply with synthetic data, "
         "reading requires real images of the target capture conditions, synthetic layouts must be varied enough, "
         "and a typed, executable target makes the organizing decisions visible and testable."])
concern(R1, 12, "The limitations and Conclusions should be more explicitly aligned with the actual experimental "
        "scope and evidence ... Clearly distinguish demonstrated capabilities from aspects that remain untested or "
        "partially supported, and revise the Conclusions to emphasize the actual scientific findings ...",
        ["Section 6.3 now contains Table 15, which classifies each capability as demonstrated, partially supported "
         "or untested, with the evidence for each: handwriting, multi-page and long tables, section rows and "
         "non-English documents are listed as untested; photographed tables from new sources, robustness to "
         "scanning and charts as partial; header–items documents as demonstrated on our layouts but not "
         "transferred to the independent invoices. The text states that the synthetic degradations are not "
         "evidence of robustness to real scans. The Conclusions were rewritten around three scientific findings "
         "(the conventions are learnable and stable across seeds; the gain comes from training on exact data "
         "rather than the SQL format, which adds keys, types and executability; synthetic and real data teach "
         "different abilities) and the documented failures, and no longer emphasize the comparison of a 2B model "
         "with larger ones."])

# ------------------------------------------------------------------ Reviewer 2 (Reviewer B)
R2 = "Reviewer#2"
concern(R2, 1, "Strengthen the experimental design by incorporating task-adapted baseline models and correcting "
        "the confounding differences between the synthetic-only and mixed-data training experiments.",
        [f"Thank you; both points led to new trainings. Task-adapted baseline: we trained the same 2B model with "
         f"exactly the same data and recipe, but with the gold rendered as HTML tables, and evaluated it on all "
         f"sets (Section 5.2). It matches PIX2DB in cell accuracy on every set (synthetic exact match "
         f"{r('synth_html2b')} vs {r('synth_ours')}; no difference is significant) but cannot express keys (FK "
         f"recall 0). We now state plainly that most of the gain over untuned models comes from training on the "
         f"conventions, and that the SQL target contributes keys, declared types and direct executability. We also "
         f"added Docling as a dedicated document-conversion system.",
         f"Confound: the first submission compared 24,000 synthetic examples with a 36,589-example mixture. We "
         f"generated 9,589 additional synthetic images and trained a synthetic-only model on 36,589 examples, the "
         f"same number as the mixture, and a real-only model on the 19,589 converted real examples (Section 4.5, "
         f"Table 8). With size fixed, synthetic-only training still transfers poorly (PubTabNet F1 "
         f"{r('ptn_synth')} vs {r('ptn_ours')}), so the effect is due to the kind of data. The real-only model "
         f"is as good as the mixture on real tables (PubTabNet {r('ptn_real')}, FinTabNet {r('ftn_real')}) but "
         f"declares no foreign key (FK recall {r('fkr_real')}), reaches {r('synth_real')} exact match on the "
         f"synthetic test, and falls behind on receipts, invoices and charts. We now state this division "
         f"explicitly: the real data teaches reading, the synthetic data teaches the relational structure."])
concern(R2, 2, "Expand the evaluation beyond cell-level accuracy and foreign-key recall to include referential "
        "integrity, foreign-key precision, schema correctness, and query-execution equivalence.",
        [f"All four were implemented and are reported (Section 3.5 defines them). Table 7 gives FK precision, "
         f"referential integrity, PK precision, table and column counts, type accuracy and query equivalence on "
         f"the synthetic test: PIX2DB declares {r('nfk_ours')} correct foreign keys (precision {r('fkp_ours')}, "
         f"8B: {r('fkp_q8')}), its referential integrity is {r('ri_ours')}, and its PK precision {r('pkp_ours')} "
         f"(8B: {r('pkp_q8')}). Query-execution equivalence uses queries generated from each gold schema (row "
         f"counts, sums, minima and maxima, distinct counts, join counts), translated through the alignment and "
         f"executed on both databases; Table 14 reports it on all eight sets. It reveals gaps that cell F1 hides, "
         f"e.g. on FinTabNet the 8B HTML pipeline has cell F1 {r('ftn_h8')} but query equivalence "
         f"{r('qe_ftn_h8')} (PIX2DB {r('qe_ftn_ours')}), because formatted numbers stay text."])
concern(R2, 3, "Validate generalizability using additional independent real-world datasets, particularly complex "
        "photographed documents and multi-table relational structures.",
        [f"We added an independent multi-table set of 490 full-page invoices from a public dataset produced by a "
         f"generator unrelated to ours, with a two-table gold database (invoice header with primary key, line "
         f"items with foreign key) (Sections 3.2.3, 4.1, 5.3). The result is negative for our model and is "
         f"reported as such: PIX2DB transcribes the item table but omits the header (cell recall "
         f"{r('inv_rec_ours')}, FK recall {r('inv_fk_ours')}), whereas the untuned 8B model reaches "
         f"{r('inv_rec_q8')} and {r('inv_fk_q8')}. Figure 4 shows a typical case, and the text explains the "
         f"failure as over-specialization to the key–value layout of the synthetic documents. For photographed "
         f"documents, TabRecSet remains the independent photographed set, now with paired significance and seed "
         f"variability; we did not find another public photographed dataset with table annotations that could be "
         f"converted to exact gold databases within the revision period and list this as a limitation "
         f"(Table 15)."])
concern(R2, 4, "Report variability across multiple training runs and clarify the practical and statistical "
        "significance of performance differences.",
        [f"Two further training runs with seeds 1 and 2 are reported in Section 4.7 and Table 12 (largest standard "
         f"deviation {r('seed_maxsd')}). For significance, every comparison in Table 13 is now accompanied by a "
         f"one-sided paired bootstrap, summarized in the table footer, and the text distinguishes significant "
         f"from non-significant differences explicitly (e.g. PubTabNet against the 8B HTML pipeline, p "
         f"{r('p_ptn_h8')}; charts against the 8B model; all differences to the task-adapted baseline). We also "
         f"discuss practical significance: training variance is an order of magnitude smaller than the "
         f"differences to the baselines, while a TabRecSet F1 of 0.52 is described as not usable without review."])
concern(R2, 5, "Investigate how the repair mechanism affects data completeness and relational integrity, "
        "especially when it removes primary-key constraints or discards invalid records.",
        [f"Section 4.6 and Table 11 now quantify this. Across 1,410 outputs, the layer drops "
         f"{r('loss_rows_pix2db-2b-v2')} gold rows that cannot be inserted and removes {r('loss_pk_pix2db-2b-v2')} "
         f"primary-key constraints because of duplicate key values; dropping a key preserves all rows but loses "
         f"the uniqueness guarantee, and each case is returned as a warning. The {r('loss_resc_pix2db-2b-v2')} "
         f"outputs rescued by the layer reach cell F1 {r('loss_rescf1_pix2db-2b-v2')} after repair. Referential "
         f"integrity after repair is reported in Table 7 ({r('ri_ours')}), and the per-strategy ablation in Table "
         f"10 shows which strategy causes which change."])
concern(R2, 6, "Reconcile dataset reporting across the manuscript, clarify the limitations of synthetic "
        "evaluation, and ensure compliance with the journal's disclosure requirements.",
        ["Dataset reporting: the new Table 2 reconciles the pool and the training counts and lists every split "
         "with its role (see Reviewer#1, Concern #4). Limits of synthetic evaluation: Sections 4.3, 5.4, 6.2 and "
         "6.3 state that the synthetic test shares layouts and conventions with training, that the synthetic "
         "degradations are moderate and not evidence of robustness to real scans, and that the independent sets "
         "give a lower and more realistic estimate. Disclosure: the back matter contains author contributions, "
         "funding, data availability with links to the model, data, code and evaluation outputs, conflicts of "
         "interest, and the preprint notice with its DOI in the Acknowledgments, as required by the Author "
         "Guidelines."])
concern(R2, 7, "The authors should clarify that the reported foreign-key recall was evaluated on synthetic data "
        "and distinguish statistically significant improvements from nonsignificant differences (Abstract).",
        [f"The Abstract was revised accordingly. It now says that foreign-key recall ({r('fkr_ours')}, with "
         f"precision {r('fkp_ours')}) was measured on the synthetic test, reports p-values for the main "
         f"comparisons and states that the PubTabNet difference to the 8B HTML pipeline is not significant "
         f"(p {r('p_ptn_h8')}). It also reports the two independent sources on which the model is weaker, the "
         f"task-adapted baseline and the seed variability."])

# ------------------------------------------------------------------ Editor
concern("Editor", 1, "Please upload the revised manuscript in an editable Microsoft Word (.docx) format.",
        ["Both the revised manuscript with yellow highlighting and the clean manuscript are provided as .docx "
         "files prepared with the J.FAITH Word template."])
concern("Editor", 2, "Please consider incorporating relevant studies published in this journal (J.FAITH) ... "
        "regarding image processing, visual recognition, or robustness under image degradation.",
        ["Thank you. Three J.FAITH articles are now cited where they support the discussion: Aduvuku et al. "
         "(2026) on efficient on-device vision foundation models, which motivates the 2B scale (Section 2.2); "
         "Ramadani et al. (2025) on low-light enhancement for detection under degraded images, in the context of "
         "robustness to capture conditions (Section 2.3, tested in Section 4.3); and Rahman et al. (2025) on "
         "synthetic data generation, in the context of our synthetic training data (Section 2.3)."])

# ------------------------------------------------------------------ assemble
WORK = HERE / "_resp"
if WORK.exists():
    shutil.rmtree(WORK)
with zipfile.ZipFile(TEMPLATE) as z:
    z.extractall(WORK)
doc = (WORK / "word/document.xml").read_text(encoding="utf-8")
head, rest = doc.split("<w:body>", 1)
sect = re.search(r"<w:sectPr.*?</w:sectPr>", rest, re.S).group(0)
# first concern starts on a new page, as in the template
first = next(i for i, b in enumerate(BODY) if "Concern # 1:" in b)
BODY[first] = BODY[first].replace("<w:pPr>", "<w:pPr><w:pageBreakBefore/>", 1)
(WORK / "word/document.xml").write_text(head + "<w:body>" + "".join(BODY) + sect + "</w:body></w:document>",
                                        encoding="utf-8")
if OUT.exists():
    OUT.unlink()
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(WORK.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(WORK).as_posix())
shutil.rmtree(WORK)
txt = re.sub(r"<[^>]+>", " ", "".join(BODY))
print(f"wrote {OUT.name}: ~{len(txt.split())} words, pending: {txt.count('[pending]')}")
