#!/usr/bin/env python3
"""V2.5 assignment-source intake helper.

This helper inventories teacher/user files, extracts deterministic native text/metadata
when possible, renders PDF pages when possible, and marks sources that require visual
inspection. It deliberately does not pretend OCR/vision happened when it did not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
from typing import Any
import xml.etree.ElementTree as ET

# Intake artifact schema version; independent of the Skill release version.
SCHEMA_VERSION = "2.4"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name: str) -> str:
    stem = re.sub(r"[^\w\-.\u4e00-\u9fff]+", "_", name, flags=re.UNICODE).strip("_")
    return stem[:120] or "source"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def infer_role(path: Path) -> list[str]:
    s = path.name.lower()
    roles: list[str] = []
    if any(x in s for x in ["模板", "template", "格式"]):
        roles.append("template")
    if any(x in s for x in ["要求", "作业", "任务", "assignment", "requirement"]):
        roles.append("assignment_sheet")
    if any(x in s for x in ["评分", "rubric", "考核"]):
        roles.append("rubric")
    if any(x in s for x in ["示例", "范文", "往届", "example", "sample"]):
        roles.append("example_paper")
    if not roles:
        roles.append("other")
    return roles


def twips_to_cm(v: str | None) -> float | None:
    try:
        return round(int(v) / 1440 * 2.54, 3) if v is not None else None
    except Exception:
        return None


def half_points_to_pt(v: str | None) -> float | None:
    try:
        return round(int(v) / 2, 2) if v is not None else None
    except Exception:
        return None


def xml_text(el: ET.Element) -> str:
    parts: list[str] = []
    for node in el.iter():
        if node.tag == qn("t") and node.text:
            parts.append(node.text)
        elif node.tag == qn("tab"):
            parts.append("\t")
        elif node.tag == qn("br"):
            parts.append("\n")
    return "".join(parts)


def parse_docx(path: Path) -> tuple[str, dict[str, Any]]:
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())
        if "word/document.xml" not in names:
            raise ValueError("word/document.xml missing")
        root = ET.fromstring(z.read("word/document.xml"))

        paragraphs: list[dict[str, Any]] = []
        tables = 0
        for p in root.findall(".//w:p", NS):
            text = xml_text(p).strip()
            pstyle = p.find("./w:pPr/w:pStyle", NS)
            style_id = pstyle.get(qn("val")) if pstyle is not None else None
            jc = p.find("./w:pPr/w:jc", NS)
            align = jc.get(qn("val")) if jc is not None else None
            if text:
                paragraphs.append({"text": text, "style_id": style_id, "alignment": align})
        tables = len(root.findall(".//w:tbl", NS))
        sdt_count = len(root.findall(".//w:sdt", NS))

        styles: dict[str, Any] = {}
        if "word/styles.xml" in names:
            sroot = ET.fromstring(z.read("word/styles.xml"))
            for st in sroot.findall(".//w:style", NS):
                sid = st.get(qn("styleId"))
                if not sid:
                    continue
                nm = st.find("./w:name", NS)
                based = st.find("./w:basedOn", NS)
                rpr = st.find("./w:rPr", NS)
                ppr = st.find("./w:pPr", NS)
                item: dict[str, Any] = {
                    "name": nm.get(qn("val")) if nm is not None else None,
                    "type": st.get(qn("type")),
                    "based_on": based.get(qn("val")) if based is not None else None,
                }
                if rpr is not None:
                    fonts = rpr.find("./w:rFonts", NS)
                    sz = rpr.find("./w:sz", NS)
                    item["font_ascii"] = fonts.get(qn("ascii")) if fonts is not None else None
                    item["font_eastAsia"] = fonts.get(qn("eastAsia")) if fonts is not None else None
                    item["size_pt"] = half_points_to_pt(sz.get(qn("val")) if sz is not None else None)
                    item["bold"] = rpr.find("./w:b", NS) is not None
                if ppr is not None:
                    jc = ppr.find("./w:jc", NS)
                    spacing = ppr.find("./w:spacing", NS)
                    ind = ppr.find("./w:ind", NS)
                    item["alignment"] = jc.get(qn("val")) if jc is not None else None
                    if spacing is not None:
                        item["spacing"] = {
                            "before_twips": spacing.get(qn("before")),
                            "after_twips": spacing.get(qn("after")),
                            "line": spacing.get(qn("line")),
                            "line_rule": spacing.get(qn("lineRule")),
                        }
                    if ind is not None:
                        item["indent"] = {
                            "left_twips": ind.get(qn("left")),
                            "right_twips": ind.get(qn("right")),
                            "firstLine_twips": ind.get(qn("firstLine")),
                            "hanging_twips": ind.get(qn("hanging")),
                        }
                styles[sid] = item

        sections: list[dict[str, Any]] = []
        for sp in root.findall(".//w:sectPr", NS):
            pgSz = sp.find("./w:pgSz", NS)
            pgMar = sp.find("./w:pgMar", NS)
            sec: dict[str, Any] = {}
            if pgSz is not None:
                sec["page_width_cm"] = twips_to_cm(pgSz.get(qn("w")))
                sec["page_height_cm"] = twips_to_cm(pgSz.get(qn("h")))
                sec["orientation"] = pgSz.get(qn("orient")) or "portrait"
            if pgMar is not None:
                sec["margins_cm"] = {
                    "top": twips_to_cm(pgMar.get(qn("top"))),
                    "right": twips_to_cm(pgMar.get(qn("right"))),
                    "bottom": twips_to_cm(pgMar.get(qn("bottom"))),
                    "left": twips_to_cm(pgMar.get(qn("left"))),
                    "header": twips_to_cm(pgMar.get(qn("header"))),
                    "footer": twips_to_cm(pgMar.get(qn("footer"))),
                }
            sections.append(sec)

        text = "\n".join(p["text"] for p in paragraphs)
        placeholders = sorted(set(re.findall(r"\{\{[^{}]{1,80}\}\}|\[[^\[\]\n]{1,40}\]|_{4,}|<[^<>\n]{1,40}>", text)))
        meta = {
            "paragraph_count": len(paragraphs),
            "table_count": tables,
            "content_control_count": sdt_count,
            "headers": sorted(n for n in names if re.match(r"word/header\d+\.xml$", n)),
            "footers": sorted(n for n in names if re.match(r"word/footer\d+\.xml$", n)),
            "sections": sections,
            "styles": styles,
            "placeholders_detected": placeholders,
            "paragraph_samples": paragraphs[:120],
        }
        return text, meta


def pdf_extract_fitz(path: Path, render_dir: Path | None, max_pages: int) -> tuple[str, dict[str, Any]]:
    import fitz  # type: ignore
    doc = fitz.open(path)
    texts: list[str] = []
    rendered: list[str] = []
    for i, page in enumerate(doc):
        try:
            texts.append(page.get_text("text") or "")
        except Exception:
            texts.append("")
        if render_dir is not None and i < max_pages:
            render_dir.mkdir(parents=True, exist_ok=True)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            out = render_dir / f"page-{i+1:03d}.png"
            pix.save(out)
            rendered.append(str(out.resolve()))
    return "\n\f\n".join(texts), {"parser": "pymupdf", "page_count": len(doc), "rendered_pages": rendered}


def pdf_extract_pypdf(path: Path) -> tuple[str, dict[str, Any]]:
    from pypdf import PdfReader  # type: ignore
    r = PdfReader(str(path))
    texts=[]
    for p in r.pages:
        try: texts.append(p.extract_text() or "")
        except Exception: texts.append("")
    return "\n\f\n".join(texts), {"parser": "pypdf", "page_count": len(r.pages), "rendered_pages": []}


def pdf_extract_pdftotext(path: Path) -> tuple[str, dict[str, Any]]:
    exe = shutil.which("pdftotext")
    if not exe: raise RuntimeError("pdftotext unavailable")
    p = subprocess.run([exe, "-layout", str(path), "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode(errors="ignore")[:500])
    txt = p.stdout.decode("utf-8", errors="replace")
    return txt, {"parser": "pdftotext", "page_count": None, "rendered_pages": []}


def render_pdf_pdftoppm(path: Path, render_dir: Path, max_pages: int) -> list[str]:
    exe = shutil.which("pdftoppm")
    if not exe: return []
    render_dir.mkdir(parents=True, exist_ok=True)
    prefix = render_dir / "page"
    cmd=[exe, "-png", "-f", "1", "-l", str(max_pages), "-r", "120", str(path), str(prefix)]
    p=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0: return []
    return [str(x.resolve()) for x in sorted(render_dir.glob("page-*.png"))]


def image_dimensions(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as im:
            return {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}
    except Exception:
        return {}


def ingest_one(src: Path, root: Path, source_id: str, copy_sources: bool, render_pdf: bool, max_render_pages: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    assignment = root / "assignment"
    extracted = assignment / "extracted"
    rendered_root = assignment / "rendered" / source_id
    source_files = assignment / "source-files"
    extracted.mkdir(parents=True, exist_ok=True)
    if copy_sources:
        source_files.mkdir(parents=True, exist_ok=True)
        dest = source_files / src.name
        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)
        stored_path = dest.resolve()
    else:
        stored_path = src.resolve()

    ext=src.suffix.lower()
    mime=mimetypes.guess_type(src.name)[0]
    entry: dict[str, Any] = {
        "source_id": source_id,
        "name": src.name,
        "original_path": str(src.resolve()),
        "stored_path": str(stored_path),
        "sha256": sha256(src),
        "size_bytes": src.stat().st_size,
        "mime": mime,
        "role_hints": infer_role(src),
        "parse_status": "unparsed",
        "source_kind": "unknown",
        "needs_vision": False,
        "vision_review_status": "not_required",
        "extracted_text_path": None,
        "metadata_path": None,
        "rendered_pages": [],
        "notes": [],
    }
    template_candidate=None

    if ext in {".txt", ".md", ".csv"}:
        text=src.read_text(encoding="utf-8", errors="replace")
        out=extracted/f"{source_id}-{safe_name(src.stem)}.txt"
        out.write_text(text, encoding="utf-8")
        entry.update(source_kind="text", parse_status="ok", extracted_text_path=str(out.resolve()))
    elif ext==".docx":
        try:
            text, meta=parse_docx(src)
            out=extracted/f"{source_id}-{safe_name(src.stem)}.txt"
            out.write_text(text, encoding="utf-8")
            mp=extracted/f"{source_id}-{safe_name(src.stem)}.docx-meta.json"
            write_json(mp, meta)
            entry.update(source_kind="docx", parse_status="ok", extracted_text_path=str(out.resolve()), metadata_path=str(mp.resolve()))
            template_candidate={
                "source_ref": source_id,
                "source_path": str(stored_path),
                "role_hints": entry["role_hints"],
                "page_setup": meta.get("sections", []),
                "styles": meta.get("styles", {}),
                "headers": meta.get("headers", []),
                "footers": meta.get("footers", []),
                "table_count": meta.get("table_count"),
                "content_control_count": meta.get("content_control_count"),
                "placeholders_detected": meta.get("placeholders_detected", []),
                "status": "candidate",
            }
        except Exception as e:
            entry.update(source_kind="docx", parse_status="error")
            entry["notes"].append(f"DOCX parse failed: {type(e).__name__}: {e}")
    elif ext==".pdf":
        text=""; meta={}; err=[]
        try:
            text, meta=pdf_extract_fitz(src, rendered_root if render_pdf else None, max_render_pages)
        except Exception as e: err.append(f"pymupdf: {type(e).__name__}: {e}")
        if not meta:
            try: text, meta=pdf_extract_pypdf(src)
            except Exception as e: err.append(f"pypdf: {type(e).__name__}: {e}")
        if not meta:
            try: text, meta=pdf_extract_pdftotext(src)
            except Exception as e: err.append(f"pdftotext: {type(e).__name__}: {e}")
        if meta:
            if render_pdf and not meta.get("rendered_pages"):
                meta["rendered_pages"] = render_pdf_pdftoppm(src, rendered_root, max_render_pages)
            out=extracted/f"{source_id}-{safe_name(src.stem)}.txt"
            out.write_text(text, encoding="utf-8")
            mp=extracted/f"{source_id}-{safe_name(src.stem)}.pdf-meta.json"
            chars=len(re.sub(r"\s+", "", text))
            pages=meta.get("page_count") or 1
            likely_scanned = chars < max(20, int(pages)*20)
            meta.update(text_char_count=chars, likely_scanned=likely_scanned)
            write_json(mp, meta)
            entry.update(source_kind="pdf", parse_status="ok", extracted_text_path=str(out.resolve()), metadata_path=str(mp.resolve()), rendered_pages=meta.get("rendered_pages", []))
            if likely_scanned:
                entry["needs_vision"]=True
                entry["vision_review_status"]="pending"
                entry["notes"].append("PDF text is sparse; likely scanned/image-heavy. Visual review required.")
                if not entry["rendered_pages"]:
                    entry["rendered_pages"] = render_pdf_pdftoppm(src, rendered_root, max_render_pages)
        else:
            entry.update(source_kind="pdf", parse_status="parser_unavailable", needs_vision=True, vision_review_status="pending")
            entry["notes"].extend(err[-3:])
            if render_pdf:
                entry["rendered_pages"] = render_pdf_pdftoppm(src, rendered_root, max_render_pages)
    elif ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        mp=extracted/f"{source_id}-{safe_name(src.stem)}.image-meta.json"
        meta=image_dimensions(src)
        write_json(mp, meta)
        entry.update(source_kind="image", parse_status="classified", needs_vision=True, vision_review_status="pending", metadata_path=str(mp.resolve()))
        entry["rendered_pages"]=[str(stored_path)]
    elif ext in {".doc", ".wps"}:
        entry.update(source_kind="legacy_document", parse_status="unsupported", needs_vision=False)
        entry["notes"].append("Legacy DOC/WPS is not parsed by this helper. Convert to DOCX/PDF or inspect with another available tool.")
    else:
        entry["notes"].append("Unsupported file type; inspect with another available tool if relevant.")
    return entry, template_candidate


def main() -> int:
    ap=argparse.ArgumentParser(description="Inventory and extract assignment files for CNKI Academic Writing V2.5")
    sub=ap.add_subparsers(dest="command", required=True)
    p=sub.add_parser("ingest")
    p.add_argument("--root", default=".")
    p.add_argument("--input", nargs="+", required=True)
    p.add_argument("--copy-sources", action="store_true")
    p.add_argument("--render-pdf-pages", action="store_true")
    p.add_argument("--max-render-pages", type=int, default=20)
    args=ap.parse_args()

    root=Path(args.root).expanduser().resolve()
    assignment=root/"assignment"
    assignment.mkdir(parents=True, exist_ok=True)
    manifest_path=assignment/"source-manifest.json"
    if manifest_path.exists():
        try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception: manifest={}
    else: manifest={}
    manifest.setdefault("schema_version", SCHEMA_VERSION)
    manifest.setdefault("sources", [])
    existing_by_hash={x.get("sha256"):x for x in manifest.get("sources",[]) if isinstance(x,dict) and x.get("sha256")}

    candidates_path=assignment/"template-candidates.json"
    if candidates_path.exists():
        try: candidates=json.loads(candidates_path.read_text(encoding="utf-8"))
        except Exception: candidates={}
    else: candidates={}
    candidates.setdefault("schema_version", SCHEMA_VERSION)
    candidates.setdefault("candidates", [])
    cand_by_ref={x.get("source_ref"):x for x in candidates.get("candidates",[]) if isinstance(x,dict)}

    next_num=1
    used={x.get("source_id") for x in manifest.get("sources",[]) if isinstance(x,dict)}
    while f"src-{next_num:04d}" in used: next_num+=1

    new_entries=[]
    for raw in args.input:
        src=Path(raw).expanduser().resolve()
        if not src.exists() or not src.is_file():
            print(json.dumps({"status":"error","path":str(src),"error":"file_not_found"}, ensure_ascii=False))
            continue
        digest=sha256(src)
        if digest in existing_by_hash:
            new_entries.append(existing_by_hash[digest])
            continue
        source_id=f"src-{next_num:04d}"; next_num+=1
        entry,candidate=ingest_one(src, root, source_id, args.copy_sources, args.render_pdf_pages, args.max_render_pages)
        manifest["sources"].append(entry); existing_by_hash[digest]=entry; new_entries.append(entry)
        if candidate:
            cand_by_ref[source_id]=candidate
    candidates["candidates"]=list(cand_by_ref.values())
    write_json(manifest_path, manifest)
    write_json(candidates_path, candidates)
    print(json.dumps({"status":"ok","root":str(root),"manifest":str(manifest_path.resolve()),"sources":new_entries}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
