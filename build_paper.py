"""Build the polished Problem C paper from Markdown with rendered formulas."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report" / "c_uav_inspection_paper.md"
OUTPUT = ROOT / "C题论文_多无人机联合巡检优化.docx"
TMP_OUTPUT = ROOT / "C题论文_多无人机联合巡检优化.tmp.docx"
REFERENCE_DOC = ROOT / "参考资料" / "数学建模论文模板.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix if prefix != "rel" else "", uri)


def _pandoc_cmd(reference_doc: Path | None) -> list[str]:
    cmd = [
        "pandoc",
        str(SOURCE),
        "--from",
        "markdown+tex_math_dollars+pipe_tables+implicit_figures",
        "--to",
        "docx",
        "--standalone",
        "--resource-path",
        str(ROOT),
        "--output",
        str(TMP_OUTPUT),
    ]
    if reference_doc and reference_doc.exists():
        cmd.extend(["--reference-doc", str(reference_doc)])
    return cmd


def _q(name: str) -> str:
    prefix, tag = name.split(":")
    return f"{{{NS[prefix]}}}{tag}"


def _child(parent: ET.Element, name: str) -> ET.Element:
    found = parent.find(_q(name))
    if found is None:
        found = ET.Element(_q(name))
        parent.insert(0, found)
    return found


def _set_attr(element: ET.Element, name: str, value: str) -> None:
    element.set(_q(name), value)


def _set_fonts(r_pr: ET.Element, east_asia: str, ascii_font: str, size_half_points: str) -> None:
    fonts = _child(r_pr, "w:rFonts")
    _set_attr(fonts, "w:eastAsia", east_asia)
    _set_attr(fonts, "w:ascii", ascii_font)
    _set_attr(fonts, "w:hAnsi", ascii_font)
    size = _child(r_pr, "w:sz")
    _set_attr(size, "w:val", size_half_points)
    size_cs = _child(r_pr, "w:szCs")
    _set_attr(size_cs, "w:val", size_half_points)


def _set_style(styles_root: ET.Element, style_id: str, *, font: str, ascii_font: str,
               size: str, bold: bool, alignment: str | None) -> None:
    style = None
    for candidate in styles_root.findall("w:style", NS):
        if candidate.get(_q("w:styleId")) == style_id:
            style = candidate
            break
    if style is None:
        style = ET.SubElement(styles_root, _q("w:style"), {_q("w:type"): "paragraph", _q("w:styleId"): style_id})
        ET.SubElement(style, _q("w:name"), {_q("w:val"): style_id})

    p_pr = _child(style, "w:pPr")
    spacing = _child(p_pr, "w:spacing")
    _set_attr(spacing, "w:before", "0")
    _set_attr(spacing, "w:after", "0")
    _set_attr(spacing, "w:line", "240")
    _set_attr(spacing, "w:lineRule", "auto")
    if alignment:
        jc = _child(p_pr, "w:jc")
        _set_attr(jc, "w:val", alignment)
    r_pr = _child(style, "w:rPr")
    _set_fonts(r_pr, font, ascii_font, size)
    if bold:
        _child(r_pr, "w:b")
        _child(r_pr, "w:bCs")


def _postprocess_docx(path: Path) -> None:
    """Apply contest Word layout rules after Pandoc renders formulas."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp_dir)

        doc_xml = tmp_dir / "word" / "document.xml"
        rels_xml = tmp_dir / "word" / "_rels" / "document.xml.rels"
        styles_xml = tmp_dir / "word" / "styles.xml"
        footer_xml = tmp_dir / "word" / "footer1.xml"

        doc_tree = ET.parse(doc_xml)
        doc_root = doc_tree.getroot()
        body = doc_root.find("w:body", NS)
        if body is None:
            raise RuntimeError("DOCX body not found")

        styles_tree = ET.parse(styles_xml)
        styles_root = styles_tree.getroot()
        _set_style(styles_root, "Normal", font="宋体", ascii_font="Times New Roman", size="24", bold=False, alignment=None)
        _set_style(styles_root, "BodyText", font="宋体", ascii_font="Times New Roman", size="24", bold=False, alignment=None)
        _set_style(styles_root, "FirstParagraph", font="宋体", ascii_font="Times New Roman", size="24", bold=False, alignment=None)
        _set_style(styles_root, "Title", font="黑体", ascii_font="SimHei", size="32", bold=True, alignment="center")
        _set_style(styles_root, "Heading1", font="黑体", ascii_font="SimHei", size="28", bold=True, alignment="center")
        _set_style(styles_root, "Heading2", font="黑体", ascii_font="SimHei", size="24", bold=True, alignment="left")
        _set_style(styles_root, "Heading3", font="黑体", ascii_font="SimHei", size="24", bold=True, alignment="left")
        _set_style(styles_root, "Caption", font="宋体", ascii_font="Times New Roman", size="24", bold=False, alignment="center")
        styles_tree.write(styles_xml, encoding="utf-8", xml_declaration=True)

        parent_map = {child: parent for parent in doc_root.iter() for child in parent}

        def in_table(element: ET.Element) -> bool:
            parent = parent_map.get(element)
            while parent is not None:
                if parent.tag == _q("w:tc"):
                    return True
                parent = parent_map.get(parent)
            return False

        paragraphs = list(body.iter(_q("w:p")))
        for idx, para in enumerate(paragraphs):
            text = "".join(t.text or "" for t in para.findall(".//w:t", NS)).strip()
            p_pr = _child(para, "w:pPr")
            p_style = p_pr.find("w:pStyle", NS)
            style = p_style.get(_q("w:val")) if p_style is not None else ""
            has_math = para.find(".//m:oMath", NS) is not None or para.find(".//m:oMathPara", NS) is not None
            math_only = has_math and not text
            table_para = in_table(para)

            if idx == 0 and text == "面向智慧社区的多无人机-物业人员联合巡检优化研究":
                style = "Title"
                if p_style is None:
                    p_style = ET.SubElement(p_pr, _q("w:pStyle"))
                _set_attr(p_style, "w:val", "Title")

            if style in {"Title", "Heading1"} or math_only:
                alignment = "center"
                first_line = None
            elif style in {"Heading2", "Heading3"} or table_para:
                alignment = "left"
                first_line = None
            elif text.startswith("图") and " " in text[:4]:
                alignment = "center"
                first_line = None
            else:
                alignment = "left"
                first_line = None if not text or text.startswith("关键词") else "420"

            jc = _child(p_pr, "w:jc")
            _set_attr(jc, "w:val", alignment)
            spacing = _child(p_pr, "w:spacing")
            _set_attr(spacing, "w:before", "0")
            _set_attr(spacing, "w:after", "0")
            _set_attr(spacing, "w:line", "240")
            _set_attr(spacing, "w:lineRule", "auto")
            ind = p_pr.find("w:ind", NS)
            if first_line:
                if ind is None:
                    ind = ET.SubElement(p_pr, _q("w:ind"))
                _set_attr(ind, "w:firstLine", first_line)
            elif ind is not None and _q("w:firstLine") in ind.attrib:
                del ind.attrib[_q("w:firstLine")]

            if style == "Title":
                east_asia, ascii_font, size, bold = "黑体", "SimHei", "32", True
            elif style == "Heading1":
                east_asia, ascii_font, size, bold = "黑体", "SimHei", "28", True
            elif style in {"Heading2", "Heading3"}:
                east_asia, ascii_font, size, bold = "黑体", "SimHei", "24", True
            else:
                east_asia, ascii_font, size, bold = "宋体", "Times New Roman", "24", False

            for run in para.findall("w:r", NS):
                if run.find("w:t", NS) is None:
                    continue
                r_pr = _child(run, "w:rPr")
                _set_fonts(r_pr, east_asia, ascii_font, size)
                if bold:
                    _child(r_pr, "w:b")
                    _child(r_pr, "w:bCs")

        for sect_pr in doc_root.findall(".//w:sectPr", NS):
            for header_ref in list(sect_pr.findall("w:headerReference", NS)):
                sect_pr.remove(header_ref)
            for footer_ref in list(sect_pr.findall("w:footerReference", NS)):
                sect_pr.remove(footer_ref)
            pg_sz = _child(sect_pr, "w:pgSz")
            _set_attr(pg_sz, "w:w", "11906")
            _set_attr(pg_sz, "w:h", "16838")
            pg_mar = _child(sect_pr, "w:pgMar")
            for side in ("top", "bottom", "left", "right"):
                _set_attr(pg_mar, f"w:{side}", "1418")
            _set_attr(pg_mar, "w:header", "708")
            _set_attr(pg_mar, "w:footer", "708")
            pg_num = _child(sect_pr, "w:pgNumType")
            _set_attr(pg_num, "w:start", "1")
            footer_ref = ET.Element(_q("w:footerReference"))
            _set_attr(footer_ref, "w:type", "default")
            footer_ref.set(_q("r:id"), "rIdPaperFooter")
            sect_pr.insert(0, footer_ref)

        footer_root = ET.Element(_q("w:ftr"))
        p = ET.SubElement(footer_root, _q("w:p"))
        p_pr = ET.SubElement(p, _q("w:pPr"))
        ET.SubElement(p_pr, _q("w:jc"), {_q("w:val"): "center"})
        for tag, attrs, text in [
            ("begin", {_q("w:fldCharType"): "begin"}, None),
            ("instr", {}, "PAGE"),
            ("separate", {_q("w:fldCharType"): "separate"}, None),
            ("text", {}, "1"),
            ("end", {_q("w:fldCharType"): "end"}, None),
        ]:
            r = ET.SubElement(p, _q("w:r"))
            r_pr = ET.SubElement(r, _q("w:rPr"))
            _set_fonts(r_pr, "宋体", "Times New Roman", "24")
            if tag in {"begin", "separate", "end"}:
                ET.SubElement(r, _q("w:fldChar"), attrs)
            elif tag == "instr":
                instr = ET.SubElement(r, _q("w:instrText"))
                instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                instr.text = text
            else:
                t = ET.SubElement(r, _q("w:t"))
                t.text = text
        ET.ElementTree(footer_root).write(footer_xml, encoding="utf-8", xml_declaration=True)

        rels_tree = ET.parse(rels_xml)
        rels_root = rels_tree.getroot()
        for rel in list(rels_root):
            if rel.get("Id") == "rIdPaperFooter":
                rels_root.remove(rel)
        ET.SubElement(
            rels_root,
            f"{{{NS['rel']}}}Relationship",
            {
                "Id": "rIdPaperFooter",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
                "Target": "footer1.xml",
            },
        )
        rels_tree.write(rels_xml, encoding="utf-8", xml_declaration=True)
        doc_tree.write(doc_xml, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in tmp_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(tmp_dir).as_posix())


def _validate_docx(path: Path) -> tuple[int, int]:
    """Return (formula_count, image_count) after lightweight DOCX validation."""
    with zipfile.ZipFile(path) as zf:
        bad_file = zf.testzip()
        if bad_file:
            raise RuntimeError(f"DOCX archive validation failed at {bad_file}")
        xml = zf.read("word/document.xml").decode("utf-8")
        formula_count = xml.count("<m:oMath")
        image_count = len([name for name in zf.namelist() if name.startswith("word/media/")])
    return formula_count, image_count


def main() -> int:
    if not SOURCE.exists():
        raise FileNotFoundError(f"missing paper source: {SOURCE}")
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc is required to render Word equations")

    reference_doc = REFERENCE_DOC if REFERENCE_DOC.exists() else None
    subprocess.run(_pandoc_cmd(reference_doc), cwd=ROOT, check=True)
    _postprocess_docx(TMP_OUTPUT)

    formula_count, image_count = _validate_docx(TMP_OUTPUT)
    if formula_count < 10:
        raise RuntimeError(
            f"expected rendered Word equations, found only {formula_count}"
        )
    if image_count < 3:
        raise RuntimeError(f"expected 3 embedded figures, found {image_count}")

    TMP_OUTPUT.replace(OUTPUT)
    print(f"论文已生成: {OUTPUT}")
    print(f"公式对象数量: {formula_count}; 图片数量: {image_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
