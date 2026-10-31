"""Build the FAITH manuscript (.docx) from the journal template.

Keeps the template package (styles, numbering, headers/footers, first-page block, line numbering) and
replaces the body with the manuscript below. Numbers come from ../numbers.tex and ../tables/*.tex, which
are generated from the evaluation results by ../make_figures.py.
"""
from __future__ import annotations

import html
import re
import shutil
import zipfile
from pathlib import Path

from PIL import Image

from refs_ieee import REFS

HERE = Path(__file__).parent
PAPER = HERE.parent
TEMPLATE = PAPER / "new_journal" / "FAITH_Template_2026.docx"
OUT = HERE / "pix2db_FAITH.docx"
WORK = HERE / "_build"

N = dict(re.findall(r"\\newcommand\{\\N(\w+)\}\{([^}]*)\}", (PAPER / "numbers.tex").read_text(encoding="utf-8")))
N = {k: v.replace("{,}", ",") for k, v in N.items()}
PREPRINT = "https://doi.org/10.21203/rs.3.rs-11467404/v1"

# ------------------------------------------------------------------ citation numbering (order of first use)
CITE_ORDER: list[str] = []


def cite(keys: str) -> str:
    nums = []
    for k in [x.strip() for x in keys.split(",")]:
        if k not in REFS:
            raise KeyError(k)
        if k not in CITE_ORDER:
            CITE_ORDER.append(k)
        nums.append(CITE_ORDER.index(k) + 1)
    nums.sort()
    parts, i = [], 0
    while i < len(nums):  # compress runs: [3]–[5]
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(f"[{nums[i]}]" if j == i else (f"[{nums[i]}], [{nums[j]}]" if j == i + 1 else f"[{nums[i]}]–[{nums[j]}]"))
        i = j + 1
    return ", ".join(parts)


# ------------------------------------------------------------------ inline markup -> runs
def runs(text: str, base_rpr: str = "") -> str:
    """Supports <i>, <b>, <code>, <sup>, <sub> and [[cite keys]]."""
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: cite(m.group(1)), text)
    out, stack = [], []
    for tok in re.split(r"(</?(?:i|b|code|sup|sub)>)", text):
        if not tok:
            continue
        m = re.fullmatch(r"<(/?)(i|b|code|sup|sub)>", tok)
        if m:
            if m.group(1):
                stack.remove(m.group(2))
            else:
                stack.append(m.group(2))
            continue
        rpr = base_rpr
        if "b" in stack:
            rpr += "<w:b/><w:bCs/>"
        if "i" in stack:
            rpr += "<w:i/><w:iCs/>"
        if "code" in stack:
            rpr += '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/><w:sz w:val="19"/>'
        if "sup" in stack:
            rpr += '<w:vertAlign w:val="superscript"/>'
        if "sub" in stack:
            rpr += '<w:vertAlign w:val="subscript"/>'
        t = html.escape(html.unescape(tok), quote=False)
        out.append(f'<w:r>{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}<w:t xml:space="preserve">{t}</w:t></w:r>')
    return "".join(out)


def para(style: str, text: str, ppr_extra: str = "", rpr: str = "") -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{ppr_extra}</w:pPr>{runs(text, rpr)}</w:p>'


BODY: list[str] = []


def H1(t): BODY.append(para("heading1FAITH", t))
def H2(t): BODY.append(para("heading2FAITH", t))
def H3(t): BODY.append(para("heading3FAITH", t))
def P(t): BODY.append(para("maintextFAITH", t))
def PC(t): BODY.append(para("punctuatetextFAITH", t))  # text right after an equation
def LEAD(t): BODY.append(para("textbeforelistFAITH", t))
def BUL(items): BODY.extend(para("bulletFAITH", x) for x in items)
def NUM(items): BODY.extend(para("numberingFAITH", x) for x in items)
def BACK(label, t): BODY.append(para("BackMatterFAITH", f"<b>{label}:</b> {t}"))


# ------------------------------------------------------------------ figures
MEDIA: list[tuple[str, Path]] = []
FIGNO = [0]
TABNO = [0]
EQNO = [0]
BODY_EMU = 7857 * 635  # text block width in the template (EMU)


def figure(path: Path, caption: str, width_frac: float = 1.0) -> str:
    FIGNO[0] += 1
    rid = f"rIdP2D{len(MEDIA) + 1}"
    MEDIA.append((rid, path))
    w, h = Image.open(path).size
    cx = int(BODY_EMU * width_frac)
    cy = int(cx * h / w)
    n = 900 + len(MEDIA)
    drawing = (
        f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{n}" name="Figure {FIGNO[0]}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{n}" name="{path.name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        '</a:graphicData></a:graphic></wp:inline></w:drawing>')
    BODY.append(f'<w:p><w:pPr><w:pStyle w:val="figureFAITH"/><w:keepNext/><w:ind w:left="2608"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr>{drawing}</w:r></w:p>')
    BODY.append(para("figurecaptionFAITH", f"<b>Figure {FIGNO[0]}.</b> {caption}"))
    return f"Figure {FIGNO[0]}"


# ------------------------------------------------------------------ tables
def table(header: list[str], rows: list[list[str]], widths: list[int], caption: str, footer: str | None = None,
          label: str | None = None, align_first_left: bool = True, size: int = 18, bold_rows=(),
          left_cols=(0,), head_size: int | None = None) -> str:
    if label is None:
        TABNO[0] += 1
        label = f"Table {TABNO[0]}"
    BODY.append(para("tablecaptionFAITH", f"<b>{label}.</b> {caption}", "<w:keepNext/>"))
    total = sum(widths)

    def cell(txt, w, top=None, bottom=None, bold=False, left=False, sz=None):
        sz = sz or size
        b = ""
        if top:
            b += f'<w:top w:val="single" w:sz="{top}" w:space="0" w:color="auto"/>'
        if bottom:
            b += f'<w:bottom w:val="single" w:sz="{bottom}" w:space="0" w:color="auto"/>'
        borders = f"<w:tcBorders>{b}</w:tcBorders>" if b else ""
        jc = '<w:jc w:val="left"/>' if left else ""
        rpr = ("<w:b/><w:bCs/>" if bold else "") + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
        ppr = ('<w:pPr><w:pStyle w:val="tablecontentFAITH"/><w:keepNext/>'
               '<w:spacing w:before="30" w:after="30" w:line="228" w:lineRule="auto"/>' + jc + "</w:pPr>")
        paras = "".join("<w:p>" + ppr + runs(line, rpr) + "</w:p>" for line in txt.split("\n"))
        return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{borders}<w:vAlign w:val="center"/></w:tcPr>{paras}</w:tc>'

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:tblInd w:w="2608" w:type="dxa"/>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="45" w:type="dxa"/><w:right w:w="45" w:type="dxa"/></w:tblCellMar>'
           f'<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    xml.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(
        cell(h, w, top=12, bottom=6, bold=True, left=(i in left_cols), sz=head_size) for i, (h, w) in enumerate(zip(header, widths))) + "</w:tr>")
    for r_i, r in enumerate(rows):
        last = r_i == len(rows) - 1
        xml.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(
            cell(c, w, bottom=12 if last else None, bold=(r_i in bold_rows), left=(i in left_cols))
            for i, (c, w) in enumerate(zip(r, widths))) + "</w:tr>")
    xml.append("</w:tbl>")
    BODY.append("".join(xml))
    if footer:
        BODY.append(para("tablefooterJCTA", footer))
    return label


# ------------------------------------------------------------------ equations (OMML)
def mr(t, plain=False):
    sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    return f'<m:r>{sty}<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{html.escape(t, quote=False)}</m:t></m:r>'


def frac(n, d): return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"
def sub(b, s): return f"<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>"
def nsum(lo, body): return f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:supHide m:val="1"/></m:naryPr><m:sub>{lo}</m:sub><m:sup/><m:e>{body}</m:e></m:nary>'
def paren(x): return f"<m:d><m:e>{x}</m:e></m:d>"


def equation(omml: str) -> str:
    EQNO[0] += 1
    BODY.append(
        '<w:tbl><w:tblPr><w:tblW w:w="7859" w:type="dxa"/><w:tblInd w:w="2608" w:type="dxa"/><w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr><w:tblGrid><w:gridCol w:w="7228"/><w:gridCol w:w="631"/></w:tblGrid>'
        f'<w:tr><w:tc><w:tcPr><w:tcW w:w="7228" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="equationFAITH"/></w:pPr><m:oMathPara><m:oMath>{omml}</m:oMath></m:oMathPara></w:p></w:tc>'
        f'<w:tc><w:tcPr><w:tcW w:w="631" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="equationFAITH"/><w:jc w:val="right"/></w:pPr>{runs(f"({EQNO[0]})")}</w:p></w:tc></w:tr></w:tbl>')
    return f"Eq. ({EQNO[0]})"


# ------------------------------------------------------------------ algorithm
def algorithm(title: str, inp: str, outp: str, steps: list[tuple[int, str]]) -> None:
    not_bold = '<w:b w:val="0"/><w:bCs w:val="0"/>'
    rows = ['<w:p><w:pPr><w:pStyle w:val="AlgorithmheadFAITH"/></w:pPr>' + runs("Algorithm 1. ") + runs(title, not_bold) + "</w:p>"]
    body = [f'<w:p><w:pPr><w:pStyle w:val="maintextFAITH"/><w:ind w:left="0" w:firstLine="0"/></w:pPr>{runs("<b>Input:</b> " + inp)}</w:p>',
            f'<w:p><w:pPr><w:pStyle w:val="maintextFAITH"/><w:ind w:left="0" w:firstLine="0"/></w:pPr>{runs("<b>Output:</b> " + outp)}</w:p>']
    for i, (lvl, s) in enumerate(steps, 1):
        body.append(f'<w:p><w:pPr><w:pStyle w:val="algorithmstepFAITH"/><w:ind w:left="{399 + 360 * lvl}" w:hanging="399"/></w:pPr>{runs(s)}</w:p>')
    BODY.append(
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="7848" w:type="dxa"/><w:tblInd w:w="2608" w:type="dxa"/>'
        '<w:tblBorders><w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/><w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/><w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/></w:tblBorders>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr><w:tblGrid><w:gridCol w:w="7848"/></w:tblGrid>'
        '<w:tr><w:tc><w:tcPr><w:tcW w:w="7848" w:type="dxa"/><w:tcBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tcBorders></w:tcPr>'
        + "".join(rows) + '</w:tc></w:tr><w:tr><w:tc><w:tcPr><w:tcW w:w="7848" w:type="dxa"/><w:tcBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="auto"/></w:tcBorders></w:tcPr>'
        + "".join(body) + "</w:tc></w:tr></w:tbl>")


# ------------------------------------------------------------------ table data from the LaTeX tables
def tex_rows(name):
    t = (PAPER / "tables" / name).read_text(encoding="utf-8")
    t = t.split("\\midrule", 1)[1].split("\\bottomrule")[0]
    rows = []
    for line in t.split("\\\\"):
        line = line.replace("\\midrule", "").strip()
        if line:
            rows.append([c.strip() for c in line.split("&")])
    return rows


def clean(c):
    c = c.replace("$\\to$", "→").replace("\\%", "%").replace("--", "–")
    c = re.sub(r"\\textbf\{([^}]*)\}", r"<b>\1</b>", c)
    c = re.sub(r"\\,\{\\tiny\[([^\]]*)\]\}", lambda m: "\n[" + m.group(1).replace(",", ", ") + "]", c)
    return c


import manuscript  # noqa: E402  (defines the text; uses the helpers above)

manuscript.write(globals())

# ------------------------------------------------------------------ references
refs_xml = [para("heading1FAITH", "References", "<w:keepNext/>")]
for i, k in enumerate(CITE_ORDER, 1):
    refs_xml.append(f'<w:p><w:pPr><w:pStyle w:val="ReferencesFAITH"/></w:pPr>{runs(f"[{i}]")}<w:r><w:tab/></w:r>{runs(REFS[k])}</w:p>')
appendix_xml = manuscript.APPENDIX_XML

# ------------------------------------------------------------------ assemble the package
if WORK.exists():
    shutil.rmtree(WORK)
with zipfile.ZipFile(TEMPLATE) as z:
    z.extractall(WORK)
doc = (WORK / "word/document.xml").read_text(encoding="utf-8")
head, rest = doc.split("<w:body>", 1)
items = re.findall(r"<w:p[ >].*?</w:p>|<w:tbl>.*?</w:tbl>|<w:sectPr.*?</w:sectPr>", rest, re.S)
sect = items[-1]
first = items[:10]
# ORCID icon: reuse the template's own icon run from the author line, linked to the author's ORCID record
orcid_run = re.search(r"<w:r(?: [^>]*)?>(?:(?!</w:r>).)*?<w:drawing>.*?</w:drawing></w:r>", first[2], re.S).group(0)
orcid_run = re.sub(r"<wp:docPr ([^>]*?)/>",
                   r'<wp:docPr \1><a:hlinkClick xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                   r'r:id="rIdORCID"/></wp:docPr>', orcid_run, count=1)
title_block = [
    para("articletypeFAITH", "Research Article"),
    para("JournalTitleFAITH", manuscript.TITLE),
    f'<w:p><w:pPr><w:pStyle w:val="AuthorNamesFAITH"/></w:pPr>{runs("Musa Peker ")}{runs("<sup>1,*</sup>")}'
    f'<w:hyperlink r:id="rIdORCID">{orcid_run}</w:hyperlink></w:p>',
    first[3],  # history / copyright box, filled by the journal
    f'<w:p><w:pPr><w:pStyle w:val="authoraffiliationFAITH"/></w:pPr>{runs("<sup>1</sup>")}<w:r><w:tab/></w:r>'
    f'{runs(manuscript.AFFILIATION)}</w:p>',
    f'<w:p><w:pPr><w:pStyle w:val="authoraffiliationFAITH"/></w:pPr>{runs("<b>*</b>")}<w:r><w:tab/></w:r>'
    f'{runs(manuscript.CORRESPONDING)}</w:p>',
    f'<w:p><w:pPr><w:pStyle w:val="abstractFAITH"/></w:pPr>{runs("<b>Abstract:</b> " + manuscript.ABSTRACT)}</w:p>',
    f'<w:p><w:pPr><w:pStyle w:val="keywordsFAITH"/></w:pPr>{runs("<b>Keywords:</b> " + manuscript.KEYWORDS)}</w:p>',
    first[9],  # separator line
]
new_doc = head + "<w:body>" + "".join(title_block + BODY + refs_xml + appendix_xml) + sect + "</w:body></w:document>"
(WORK / "word/document.xml").write_text(new_doc, encoding="utf-8")

# media + relationships
rels_p = WORK / "word/_rels/document.xml.rels"
rels = rels_p.read_text(encoding="utf-8")
(WORK / "word/media").mkdir(exist_ok=True)
add = []
for rid, path in MEDIA:
    target = f"media/p2d_{path.name}"
    shutil.copy(path, WORK / "word" / target)
    add.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>')
add.append('<Relationship Id="rIdORCID" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
           f'hyperlink" Target="https://orcid.org/{manuscript.ORCID}" TargetMode="External"/>')
rels_p.write_text(rels.replace("</Relationships>", "".join(add) + "</Relationships>"), encoding="utf-8")
ct_p = WORK / "[Content_Types].xml"
ct = ct_p.read_text(encoding="utf-8")
if 'Extension="png"' not in ct:
    ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
ct_p.write_text(ct, encoding="utf-8")

# running header: first author's last name
for h in (WORK / "word").glob("header*.xml"):
    x = h.read_text(encoding="utf-8")
    x = x.replace("> Last name Author</w:t>", "> Peker</w:t>").replace("> of First Author</w:t>", "></w:t>")
    x = x.replace("<w:t>, et al.</w:t>", "<w:t></w:t>")
    h.write_text(x, encoding="utf-8")

if OUT.exists():
    OUT.unlink()
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(WORK.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(WORK).as_posix())
shutil.rmtree(WORK)
words = len(re.sub(r"<[^>]+>", " ", "".join(BODY)).split())
print(f"wrote {OUT.name}: {FIGNO[0]} figures, {TABNO[0]} tables, {EQNO[0]} equations, {len(CITE_ORDER)} references, ~{words} body words")
unused = [k for k in REFS if k not in CITE_ORDER]
print("unused refs:", unused)
