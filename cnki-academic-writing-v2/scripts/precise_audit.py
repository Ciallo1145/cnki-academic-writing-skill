#!/usr/bin/env python3
"""Low-token static pre-scan for precise academic claim auditing.

This script does NOT decide whether a claim is true or whether text was AI-written.
It builds focused queues for (1) risky academic claims and (2) suspiciously mechanical
writing structures so an agent can verify or revise only the places that merit attention.
Supports .md/.txt and .docx without third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SCHEMA_VERSION = "2.7"
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

STRONG_TERMS = [
    "显著优于", "明显优于", "远高于", "最高", "最低", "最优", "最佳", "唯一",
    "全部", "完全", "均能", "均为", "普遍", "广泛证明", "证明了", "充分证明",
    "必然", "根本", "彻底", "免去", "消除", "解决了", "不存在", "共识",
    "决定性", "大幅提升", "显著提升", "显著降低", "明显提升", "明显降低",
    "会高于", "必定", "一定",
]
CAUSAL_TERMS = ["导致", "造成", "决定", "使得", "因此", "从而", "证明", "表明", "说明"]
COMPARATIVE_TERMS = ["优于", "高于", "低于", "提升", "下降", "增加", "减少", "领先", "落后", "相当于", "接近"]
# These terms are not automatically false. They raise an evidence-sufficiency question:
# is one cited source enough to present the wording as a general fact, or should the claim
# be attributed to that source / softened / triangulated?
GENERALITY_TERMS = [
    "业内共识", "业界共识", "学界共识", "公认", "普遍认为", "普遍被认为",
    "首要", "最主要", "最核心", "最重要", "必经之路", "唯一途径", "普遍适用",
]
METRIC_TERMS = [
    "时延", "延迟", "速率", "吞吐量", "准确率", "正确率", "检测概率", "误码率",
    "精度", "误差", "RMSE", "SNR", "信噪比", "带宽", "频率", "多普勒", "增益",
    "功率", "覆盖", "轨道高度", "复杂度",
]
# Pairs that often indicate definition mismatch when values from different sources are
# placed in one paragraph. This is intentionally narrow to avoid flooding MEDIUM.
METRIC_QUALIFIER_PAIRS = [
    ("单向", "往返"), ("单向", "RTT"), ("平均", "峰值"), ("平均", "最大"),
    ("均值", "峰值"), ("仿真", "实测"), ("模拟", "实测"), ("上行", "下行"),
    ("每用户", "总吞吐"), ("单用户", "系统总"),
]
ATTRIBUTION_RE = re.compile(
    r"(?:文献\s*\[[^\]]+\]|该文|该研究|研究者|作者|[^，。；;]{1,18}等)"
    r"(?:认为|指出|提出|强调|总结|报告|观察到|给出|显示)"
)

STRONG_ATTRIBUTION_RES = [
    re.compile(r"文献\s*\[[^\]]+\].{0,24}(?:认为|指出|表明|证明|发现|建议|提出|报告|观察到|给出|显示)"),
    re.compile(r"(?:已有研究|既有研究|相关研究|研究表明|研究发现|研究指出|也有研究|也有工作).{0,120}\[[^\]]+\]"),
    re.compile(r"(?:据|根据)\s*文献\s*\[[^\]]+\]"),
]

# Lexical AI-style hints are deliberately small and weak. V2.5.3 relies more on
# structural patterns than on trying to enumerate every possible phrase.
AI_PHRASES = [
    "随着", "不断发展", "具有重要意义", "具有重要的理论意义", "具有重要的现实意义",
    "具有广阔的应用前景", "值得注意的是", "综上所述", "由此可见", "不难发现",
    "毋庸置疑", "可以看出", "总的来说", "从某种意义上说", "为相关领域提供参考",
    "具有一定借鉴意义", "进一步推动", "赋能", "助力", "奠定坚实基础",
]
STRUCTURE_MARKERS = [
    "首先", "其次", "再次", "最后", "第一", "第二", "第三", "第四",
    "一方面", "另一方面", "数据层面", "模型层面", "泛化层面", "部署层面",
]
PARAGRAPH_START_CONNECTORS = [
    "此外", "同时", "与此同时", "另一方面", "因此", "由此", "进一步", "总体来看", "总体看", "最后",
]
SUMMARY_SECTION_HINTS = ("摘要", "结论", "总结", "结语")

CIT_RE = re.compile(r"\[(\d+(?:\s*[-–—]\s*\d+)?(?:\s*[,，]\s*\d+(?:\s*[-–—]\s*\d+)?)*)\]")
NUM_RE = re.compile(r"(?<![A-Za-z])[-−]?\d+(?:\.\d+)?\s*(?:%|％|dB|db|ms|s|秒|分钟|h|小时|M|K|GB|MB|MHz|GHz|kHz|Hz|倍|个百分点|类|层|头|个|篇|页|万|亿)?")
HEAD_RE = re.compile(r"^(?:#{1,6}\s+.+|\d+(?:\.\d+)*\s+.+|[一二三四五六七八九十]+[、.]\s*.+|摘要\s*[:：]?|结论\s*[:：]?)$")
SENT_SPLIT_RE = re.compile(r"(?<=[。！？；;])")
REF_ENTRY_RE = re.compile(r"^\[(\d+)\]\s*")
FORMULA_NO_RE = re.compile(r"[（(]\s*(\d{1,3})\s*[)）]\s*$")
FORMULA_XREF_RE = re.compile(r"式\s*[（(]\s*(\d{1,3})\s*[)）]")
MATH_HINT_RE = re.compile(r"(?:=|≈|≤|≥|√|σ|γ|\bQ\s*\(|\b(?:sin|cos|tan|log|ln|exp)\s*\()", re.I)

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _node_text(node: ET.Element) -> str:
    """Collect both normal Word text (w:t) and OMML math text (m:t)."""
    return "".join((el.text or "") for el in node.iter() if el.tag.endswith("}t"))


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        raw = z.read("word/document.xml")
    root = ET.fromstring(raw)
    blocks: list[str] = []
    body = root.find(f"{W_NS}body")
    if body is None:
        return ""
    for node in body:
        if node.tag == f"{W_NS}p":
            s = _node_text(node).strip()
            if s:
                blocks.append(s)
        elif node.tag == f"{W_NS}tbl":
            for tr in node.iter(f"{W_NS}tr"):
                cells = []
                for tc in tr.findall(f"{W_NS}tc"):
                    c = _node_text(tc).strip()
                    if c:
                        cells.append(c)
                if cells:
                    blocks.append(" | ".join(cells))
    return "\n".join(blocks)


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return read_docx(path)
    return path.read_text(encoding="utf-8-sig", errors="replace")


def strong_attribution_site(sent: str, citations: list[int]) -> bool:
    """High-yield citation-site fidelity trigger, intentionally narrower than all cited prose."""
    return bool(citations) and any(rx.search(sent) for rx in STRONG_ATTRIBUTION_RES)


def _run_is_vanished(rpr: ET.Element | None) -> bool:
    if rpr is None:
        return False
    v = rpr.find(f"{W_NS}vanish")
    if v is None:
        return False
    val = (v.get(f"{W_NS}val") or "1").strip().lower()
    return val not in {"0", "false", "off", "none"}


def _explicit_run_color(rpr: ET.Element | None) -> str | None:
    if rpr is None:
        return None
    c = rpr.find(f"{W_NS}color")
    if c is None:
        return None
    val = (c.get(f"{W_NS}val") or "").strip().upper().lstrip("#")
    return val or None


def _near_white_hex(value: str | None) -> bool:
    if not value or value in {"AUTO", "NONE"}:
        return False
    if len(value) == 3 and all(ch in "0123456789ABCDEF" for ch in value):
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or any(ch not in "0123456789ABCDEF" for ch in value):
        return False
    r, g, b = (int(value[i:i+2], 16) for i in (0, 2, 4))
    return min(r, g, b) >= 245


def _cell_fill(tc: ET.Element) -> str | None:
    tcpr = tc.find(f"{W_NS}tcPr")
    if tcpr is None:
        return None
    shd = tcpr.find(f"{W_NS}shd")
    if shd is None:
        return None
    val = (shd.get(f"{W_NS}fill") or "").strip().upper().lstrip("#")
    return val or None


def docx_table_visibility_findings(path: Path) -> list[dict[str, Any]]:
    """Narrow high-confidence precheck for XML-nonempty table cells that may render blank.

    This intentionally does not attempt full visual reconstruction or style inheritance. It only
    catches explicit all-white/near-white text on an unshaded cell, or text runs explicitly marked
    vanished. Final rendered-page inspection remains authoritative.
    """
    if path.suffix.lower() != ".docx":
        return []
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for ti, tbl in enumerate(root.iter(f"{W_NS}tbl"), 1):
        for ri, tr in enumerate(tbl.findall(f"{W_NS}tr"), 1):
            for ci, tc in enumerate(tr.findall(f"{W_NS}tc"), 1):
                cell_text = _node_text(tc).strip()
                if not cell_text:
                    continue
                text_runs: list[tuple[str, str | None, bool]] = []
                for r in tc.iter(f"{W_NS}r"):
                    txt = "".join((t.text or "") for t in r.iter(f"{W_NS}t")).strip()
                    if not txt:
                        continue
                    rpr = r.find(f"{W_NS}rPr")
                    text_runs.append((txt, _explicit_run_color(rpr), _run_is_vanished(rpr)))
                if not text_runs:
                    continue
                fill = _cell_fill(tc)
                all_vanished = all(v for _, _, v in text_runs)
                all_explicit_near_white = all(_near_white_hex(c) for _, c, v in text_runs if not v) and any(not v for _, _, v in text_runs)
                unshaded_or_light = fill is None or _near_white_hex(fill) or fill in {"AUTO", "NONE"}
                issue = None
                if all_vanished:
                    issue = "all-text-runs-explicitly-hidden"
                elif all_explicit_near_white and unshaded_or_light:
                    issue = "all-visible-text-explicit-near-white-on-unshaded/light-cell"
                if not issue:
                    continue
                out.append({
                    "visibility_id": f"tablevis-{len(out)+1:04d}",
                    "table": ti,
                    "row": ri,
