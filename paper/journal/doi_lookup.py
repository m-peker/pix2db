"""Look up DOIs on Crossref by title and keep only confident matches (title similarity >= 0.9)."""
import json, re, time, urllib.parse, urllib.request
from difflib import SequenceMatcher

TITLES = {
 "yu2018spider": "Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task",
 "li2023bird": "Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs",
 "lei2025spider2": "Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows",
 "zheng2024multimodal": "Multimodal Table Understanding",
 "hu2022lora": "LoRA: Low-Rank Adaptation of Large Language Models",
 "kwon2023vllm": "Efficient Memory Management for Large Language Model Serving with PagedAttention",
 "zhong2020pubtabnet": "Image-Based Table Recognition: Data, Model, and Evaluation",
 "zheng2021gte": "Global Table Extractor (GTE): A Framework for Joint Table Identification and Cell Structure Recognition Using Visual Context",
 "park2019cord": "CORD: A Consolidated Receipt Dataset for Post-OCR Parsing",
 "yang2023tabrecset": "A large-scale dataset for end-to-end table recognition in the wild",
 "smock2022pubtables": "PubTables-1M: Towards comprehensive table extraction from unstructured documents",
 "smock2023aligning": "Aligning Benchmark Datasets for Table Structure Recognition",
 "nassar2022tableformer": "TableFormer: Table Structure Understanding with Transformers",
 "long2021wtw": "Parsing Table Structures in the Wild",
 "kim2022donut": "OCR-Free Document Understanding Transformer",
 "lee2023pix2struct": "Pix2Struct: Screenshot Parsing as Pretraining for Visual Language Understanding",
 "xu2020layoutlm": "LayoutLM: Pre-training of Text and Layout for Document Image Understanding",
 "liu2023deplot": "DePlot: One-shot visual language reasoning by plot-to-table translation",
 "liu2023matcha": "MatCha: Enhancing Visual Language Pretraining with Math Reasoning and Chart Derendering",
 "masry2023unichart": "UniChart: A Universal Vision-language Pretrained Model for Chart Comprehension and Reasoning",
 "masry2022chartqa": "ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning",
 "methani2020plotqa": "PlotQA: Reasoning over Scientific Plots",
 "mathew2021docvqa": "DocVQA: A Dataset for VQA on Document Images",
 "gupta2016synthtext": "Synthetic Data for Text Localisation in Natural Images",
 "kuhn1955hungarian": "The Hungarian method for the assignment problem",
 # additional references
 "gobel2013icdar": "ICDAR 2013 Table Competition",
 "zhong2019publaynet": "PubLayNet: Largest Dataset Ever for Document Layout Analysis",
 "li2020tablebank": "TableBank: Table Benchmark for Image-based Table Detection and Recognition",
 "prasad2020cascadetabnet": "CascadeTabNet: An approach for end to end table detection and structure recognition from image-based documents",
 "schreiber2017deepdesrt": "DeepDeSRT: Deep Learning for Detection and Structure Recognition of Tables in Document Images",
 "paliwal2019tablenet": "TableNet: Deep Learning Model for End-to-end Table Detection and Tabular Data Extraction from Scanned Document Images",
 "huang2022layoutlmv3": "LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking",
 "wang2020ratsql": "RAT-SQL: Relation-Aware Schema Encoding and Linking for Text-to-SQL Parsers",
 "scholak2021picard": "PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models",
 "pourreza2023dinsql": "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction",
 "dettmers2023qlora": "QLoRA: Efficient Finetuning of Quantized LLMs",
}
out = {}
for key, title in TITLES.items():
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5,
                                "select": "DOI,title,container-title,published,author,page,volume,issue,type,event"})
    try:
        with urllib.request.urlopen("https://api.crossref.org/works?" + q, timeout=30) as r:
            items = json.load(r)["message"]["items"]
    except Exception as e:  # noqa: BLE001
        print(key, "ERROR", e); continue
    best, score = None, 0
    for it in items:
        t = (it.get("title") or [""])[0]
        s = SequenceMatcher(None, re.sub(r"\W+", " ", t.lower()), re.sub(r"\W+", " ", title.lower())).ratio()
        if s > score:
            best, score = it, s
    if best and score >= 0.9:
        out[key] = {"doi": best["DOI"], "title": best["title"][0], "venue": (best.get("container-title") or [""])[0],
                    "year": (best.get("published") or {}).get("date-parts", [[None]])[0][0], "type": best.get("type"),
                    "pages": best.get("page"), "volume": best.get("volume"), "issue": best.get("issue"),
                    "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in best.get("author", [])],
                    "score": round(score, 3)}
        print(f"{key:24s} {score:.2f} {best['DOI']}  | {out[key]['venue'][:60]} {out[key]['year']}")
    else:
        print(f"{key:24s} NO MATCH (best {score:.2f})")
    time.sleep(0.3)
json.dump(out, open("dois.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
