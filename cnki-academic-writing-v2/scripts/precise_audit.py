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
                    "cell": ci,
                    "text": cell_text,
                    "issue": issue,
                    "explicit_colors": sorted({c for _, c, _ in text_runs if c}),
                    "cell_fill": fill,
                    "severity": "high",
                    "review_status": "pending",
                    "resolution": None,
                    "rendered_confirmation": None,
                    "notes": None,
                })
    return out


def citation_ids(blob: str) -> list[int]:
    ids: list[int] = []
    for part in re.split(r"[,，]", blob):
        part = part.strip()
        m = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", part)
        if m:
            a, b = map(int, m.groups())
            if 0 < b - a <= 50:
                ids.extend(range(a, b + 1))
            else:
                ids.extend([a, b])
        elif part.isdigit():
            ids.append(int(part))
    return sorted(set(ids))


def infer_section(line: str, current: str) -> str:
    s = line.strip()
    if not s:
        return current
    if s.startswith("#"):
        return s.lstrip("# ").strip()
    if HEAD_RE.match(s) and len(s) <= 80:
        return s
    return current


def risk_score(tags: list[str], nums: list[str], strong: list[str], cites: list[int]) -> int:
    score = 0
    score += 3 if strong else 0
    score += 2 if nums else 0
    score += 2 if "citation-cluster" in tags else 0
    score += 2 if "summary-claim" in tags else 0
    score += 1 if "causal-claim" in tags else 0
    score += 1 if "comparative-claim" in tags else 0
    score += 2 if "evidence-sufficiency-review" in tags else 0
    score += 2 if "cross-source-metric-check" in tags else 0
    score += 3 if "attribution-evidence-check" in tags else 0
    score += 2 if (nums or strong) and not cites else 0
    return score


def risk_level_from_score(score: int) -> str:
    return "high" if score >= 5 else "medium" if score >= 2 else "low"


def load_audit_level(root: Path, requested: str = "auto") -> str:
    if requested in {"low", "medium", "high"}:
        return requested
    cfg = root / "assignment" / "workflow-config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8-sig"))
            level = str(data.get("audit_level", "")).lower()
            if level in {"low", "medium", "high"}:
                return level
        except Exception:
            pass
    return "medium"


def style_only_claim(c: dict[str, Any]) -> bool:
    tags = set(c.get("risk_tags", []))
    return bool(tags) and tags.issubset({"ai-template-phrase", "over-structured-sentence"})


def material_medium_claim(c: dict[str, Any]) -> bool:
    """Return True for MEDIUM candidates that materially affect correctness/argument.

    V2.5.6 deliberately does not equate `risk_level == medium` with `must review`.
    This keeps MEDIUM a balanced audit instead of a near-HIGH full queue.
    """
    tags = set(c.get("risk_tags", []))
    if tags & {
        "strong-claim", "citation-cluster", "evidence-sufficiency-review", "attribution-evidence-check",
    }:
        return True
    if "summary-claim" in tags and tags & {"comparative-claim", "causal-claim", "claim-without-inline-citation"}:
        return True
    if "claim-without-inline-citation" in tags and tags & {"comparative-claim", "causal-claim"}:
        return True
    if {"comparative-claim", "causal-claim"}.issubset(tags):
        return True
    return False


def claim_required_for_level(c: dict[str, Any], level: str) -> bool:
    risk = c.get("risk_level")
    tags = set(c.get("risk_tags", []))
    # Every level keeps exact numerical claims, high-risk claims, and explicit source-attribution fidelity checks in scope.
    if risk == "high" or "numeric-claim" in tags or "attribution-evidence-check" in tags:
        return True
    if level == "low":
        return False
    if level == "medium":
        return risk == "medium" and material_medium_claim(c)
    # HIGH: all non-style-only technical claim candidates.
    return not style_only_claim(c)


def style_required_for_level(finding: dict[str, Any], level: str) -> bool:
    severity = finding.get("severity", "low")
    if level == "low":
        return severity == "high"
    if level == "medium":
        return severity in {"high", "medium"}
    return True


def metric_finding_required_for_level(finding: dict[str, Any], level: str) -> bool:
    severity = finding.get("severity", "medium")
    if level == "low":
        return severity == "high"
    return True  # MEDIUM/HIGH review all focused cross-source metric findings.


def chinese_ordinal_value(token: str) -> int | None:
    token = token.strip()
    if token in CN_NUM:
        return CN_NUM[token]
    # Enough for the structural patterns we care about; avoid pretending to be
    # a complete Chinese-number parser.
    if token.startswith("十") and len(token) == 2 and token[1] in CN_NUM:
        return 10 + CN_NUM[token[1]]
    if token.endswith("十") and len(token) == 2 and token[0] in CN_NUM:
        return CN_NUM[token[0]] * 10
    return None


def detect_enumerators(line: str) -> list[tuple[str, int, str]]:
    """Find ordered prose markers at paragraph or sentence starts.

    A single DOCX paragraph may contain several logical list items, so V2.5.3 scans
    after sentence punctuation as well as at the physical paragraph start.
    """
    s = line.strip()
    out: list[tuple[int, str, int, str]] = []
    boundary = r"(?:^|(?<=[。！？；;]))\s*"
    patterns = [
        ("qi-series", re.compile(boundary + r"其([一二三四五六七八九十]{1,3})(?:是|为|在|：|:|、|，|,|\s)")),
        ("di-series", re.compile(boundary + r"第([一二三四五六七八九十]{1,3})(?:[，,、。：:]|是|为|\s)")),
        ("yi-shi-series", re.compile(boundary + r"([一二三四五六七八九十]{1,3})是(?:\s|[^一二三四五六七八九十])")),
    ]
    for family, rx in patterns:
        for m in rx.finditer(s):
            v = chinese_ordinal_value(m.group(1))
            if v is not None:
                out.append((m.start(), family, v, m.group(0).strip()))
    lexical = [(1, "首先"), (2, "其次"), (3, "再次"), (98, "随后"), (99, "最后")]
    for v, token in lexical:
        rx = re.compile(boundary + re.escape(token))
        for m in rx.finditer(s):
            out.append((m.start(), "transition-series", v, token))
    out.sort(key=lambda x: x[0])
    return [(family, v, token) for _, family, v, token in out]


def normalized_paragraph_opener(line: str) -> str | None:
    s = re.sub(r"\s+", "", line.strip())
    if not s:
        return None
    if re.match(r"^其[一二三四五六七八九十]{1,3}(?:是|为|在)", s):
        return "其<序数>是/为"
    if re.match(r"^第[一二三四五六七八九十]{1,3}(?:[，、。：]|是|为)", s):
        return "第<序数>"
    if re.match(r"^[一二三四五六七八九十]{1,3}是", s):
        return "<序数>是"
    if re.match(r"^(首先|其次|再次|最后)", s):
        return "顺序连接词"
    if re.match(r"^从.{1,16}(层面|方面|维度|角度)(看|来看|分析|而言|出发)?", s):
        return "从…层面/方面/维度"
    if re.match(r"^(在|对于).{1,18}(层面|方面|场景|条件)(下|中|而言|上)?", s):
        return "在/对于…层面/场景"
    return None


def paragraph_start_connector(line: str) -> str | None:
    s = line.strip()
    for token in PARAGRAPH_START_CONNECTORS:
        if s.startswith(token):
            return token
    return None


def section_structural_findings(paragraphs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Detect section-level structural regularity without an exhaustive phrase blacklist."""
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in paragraphs:
        by_section[p["section"]].append(p)

    findings: list[dict[str, Any]] = []
    section_scores: dict[str, int] = {}

    def add(section: str, pattern_type: str, severity: str, ps: list[dict[str, Any]], detail: str, score_add: int, metrics: dict[str, Any] | None = None) -> None:
        fid = f"style-{len(findings)+1:04d}"
        unique_ps=[]
        seen=set()
        for para in ps:
            key=para["paragraph"]
            if key not in seen:
                seen.add(key); unique_ps.append(para)
        findings.append({
            "style_id": fid,
            "section": section,
            "pattern_type": pattern_type,
            "severity": severity,
            "paragraphs": [p["paragraph"] for p in unique_ps],
            "snippets": [p["text"][:180] for p in unique_ps[:6]],
            "detail": detail,
            "metrics": metrics or {},
            "review_status": "pending",
            "resolution": None,
            "notes": None,
        })
        section_scores[section] = min(100, section_scores.get(section, 0) + score_add)

    for section, ps in by_section.items():
        section_scores.setdefault(section, 0)
        if not ps:
            continue

        # 1) Ordered-enumeration sequence: catch 其一/其二/… regardless of the exact wording after it.
        fams: dict[str, list[tuple[dict[str, Any], int, str]]] = defaultdict(list)
        for p in ps:
            for enum in p.get("enumerators", []):
                fam, val, token = enum
                fams[fam].append((p, val, token))
        for fam, items in fams.items():
            if len(items) < 3:
                continue
            vals = [v for _, v, _ in items]
            # Preserve paragraph order; require mostly forward progression to avoid random incidental hits.
            forward = sum(1 for a, b in zip(vals, vals[1:]) if b > a)
            if forward < max(1, len(vals) - 2):
                continue
            sev = "high" if len(items) >= 4 else "medium"
            add(
                section,
                "ordered-enumeration-sequence",
                sev,
                [x[0] for x in items],
                f"Detected {len(items)} ordered prose markers in one section ({', '.join(x[2] for x in items[:6])}). Repeated enumeration may be legitimate, but a long perfectly ordered series is a structural review target.",
                45 if sev == "high" else 30,
                {"family": fam, "count": len(items), "ordinals": vals},
            )

        # 2) Repeated paragraph-opening template. This catches paraphrased but mechanically parallel starts.
        opener_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for p in ps:
            if p.get("opener_template"):
                opener_groups[p["opener_template"]].append(p)
        for opener, ops in opener_groups.items():
            if len(ops) >= 3:
                add(
                    section,
                    "repeated-paragraph-opener",
                    "medium" if len(ops) < 5 else "high",
                    ops,
                    f"{len(ops)} paragraphs share the same opening template `{opener}`.",
                    25 if len(ops) < 5 else 35,
                    {"template": opener, "count": len(ops)},
                )

        # 3) Connector-at-paragraph-start density: pattern-based, not a ban on any single connector.
        connector_ps = [p for p in ps if p.get("start_connector")]
        if len(ps) >= 4 and len(connector_ps) >= 3 and len(connector_ps) / len(ps) >= 0.5:
            counts = Counter(p["start_connector"] for p in connector_ps)
            add(
                section,
                "connector-start-density",
                "medium",
                connector_ps,
                f"{len(connector_ps)}/{len(ps)} body paragraphs begin with discourse connectors; inspect whether transitions are mechanically repeated.",
                18,
                {"paragraph_count": len(ps), "connector_paragraphs": len(connector_ps), "connector_counts": dict(counts)},
            )

        # 4) Length symmetry: weak signal only. It is never proof and should not trigger LOW/MEDIUM by itself.
        lens = [p["length"] for p in ps if p["length"] >= 40]
        if len(lens) >= 5:
            mean = sum(lens) / len(lens)
            variance = sum((x - mean) ** 2 for x in lens) / len(lens)
            cv = math.sqrt(variance) / mean if mean else 1.0
            ratio = max(lens) / max(min(lens), 1)
            if cv <= 0.14 and ratio <= 1.55:
                add(
                    section,
                    "paragraph-length-symmetry",
                    "low",
                    [p for p in ps if p["length"] >= 40],
                    "Paragraph lengths are unusually uniform. This is only a weak structural signal; keep it if the content naturally requires parallel treatment.",
                    8,
                    {"count": len(lens), "mean_chars": round(mean, 1), "cv": round(cv, 3), "max_min_ratio": round(ratio, 2)},
                )

    return findings, section_scores


def cross_source_metric_findings(paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for p in paragraphs:
        if not p.get("cross_source_metric"):
            continue
        pairs = p.get("metric_qualifier_pairs", [])
        severe = any(set(pair) & {"单向", "往返", "RTT"} for pair in pairs)
        findings.append({
            "metric_id": f"metric-{len(findings)+1:04d}",
            "section": p.get("section"),
            "paragraph": p.get("paragraph"),
            "text": p.get("text"),
            "citations": p.get("citations", []),
            "numbers": p.get("numbers", []),
            "metric_terms": p.get("metric_terms", []),
            "qualifier_pairs": pairs,
            "severity": "high" if severe else "medium",
            "review_status": "pending",
            "verdict": None,
            "revision": None,
            "notes": None,
        })
    return findings


def _normalized_heading(line: str) -> str:
    return re.sub(r"\s+", "", line).lower()


def _is_reference_heading(line: str) -> bool:
    h = _normalized_heading(line)
    return h in {"参考文献", "参考资料", "references", "reference"} or h.startswith("#参考文献")


def _delimiter_problem(text: str) -> str | None:
    pairs = {')': '(', ']': '[', '}': '{', '）': '（', '】': '【'}
    opens = set(pairs.values())
    stack: list[tuple[str, int]] = []
    for i, ch in enumerate(text):
        if ch in opens:
            stack.append((ch, i))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                return f"mismatched closing delimiter `{ch}` at char {i + 1}"
            stack.pop()
    if stack:
        ch, i = stack[-1]
        return f"unclosed delimiter `{ch}` opened at char {i + 1}"
    return None


def _dual_validation_reasons(text: str) -> list[str]:
    """Return conservative static signals for formulas that deserve two-path validation.

    This is intentionally a queueing heuristic, not a truth/complexity oracle. The agent
    must still escalate semantically complex formulas the heuristic does not recognize.
    """
    reasons: list[str] = []
    q_terms = len(re.findall(r"Q\s*\(", text))
    if q_terms >= 2:
        reasons.append("multiple-probability-tail-terms")
    if re.search(r"[∫∑ΣΠ]", text) or re.search(r"\b(?:sum|integral|expectation|Pr|Prob)\s*[\[(]", text, flags=re.I):
        reasons.append("probability-or-aggregate-expression")
    if re.search(r"\b(?:min|max|argmin|argmax)\s*\(", text, flags=re.I):
        reasons.append("decision-or-optimization-operator")
    if re.search(r"≈|\bapprox\b", text, flags=re.I) and re.search(r"[+−-].*[+−-]", text):
        reasons.append("multi-term-approximation")
    return reasons


def formula_review_findings(lines: list[str]) -> list[dict[str, Any]]:
    referenced: set[int] = set()
    for line in lines:
        for m in FORMULA_XREF_RE.finditer(line):
            referenced.add(int(m.group(1)))

    findings: list[dict[str, Any]] = []
    in_refs = False
    for pno, line in enumerate(lines, 1):
        if not line:
            continue
        if _is_reference_heading(line):
            in_refs = True
            continue
        if in_refs:
            continue
        m = FORMULA_NO_RE.search(line)
        if not m:
            continue
        formula_text = line[:m.start()].strip()
        if not formula_text or not MATH_HINT_RE.search(formula_text):
            continue
        eqno = int(m.group(1))
        syntax_issue = _delimiter_problem(formula_text)
        dual_reasons = _dual_validation_reasons(formula_text)
        findings.append({
            "formula_id": f"formula-{eqno:04d}",
            "equation_no": eqno,
            "paragraph": pno,
            "text": formula_text,
            "referenced_in_prose": eqno in referenced,
            "syntax_issue": syntax_issue,
            "severity": "high" if syntax_issue else ("medium" if eqno in referenced else "low"),
            "review_status": "pending",
            "verdict": None,
            "verification_method": None,
            "verification_note": None,
            "dual_validation_required": bool(dual_reasons),
            "dual_validation_reasons": dual_reasons,
            "verification_paths": [],
            "revision": None,
        })
    return findings


def formula_required_for_level(f: dict[str, Any], level: str) -> bool:
    if f.get("syntax_issue"):
        return True
    if f.get("referenced_in_prose"):
        return True
    return level == "high"


def reference_usage_findings(lines: list[str]) -> list[dict[str, Any]]:
    in_refs = False
    body_citations: set[int] = set()
    references: dict[int, tuple[int, str]] = {}
    for pno, line in enumerate(lines, 1):
        if not line:
            continue
        if _is_reference_heading(line):
            in_refs = True
            continue
        if in_refs:
            m = REF_ENTRY_RE.match(line)
            if m:
                references[int(m.group(1))] = (pno, line)
            continue
        for blob in CIT_RE.findall(line):
            body_citations.update(citation_ids(blob))

    findings: list[dict[str, Any]] = []
    for rid, (pno, line) in sorted(references.items()):
        if rid not in body_citations:
            findings.append({
                "reference_id": f"ref-usage-{rid:04d}",
                "reference_no": rid,
                "issue": "uncited-reference",
                "paragraph": pno,
                "text": line,
                "review_status": "pending",
                "resolution": None,
                "revision": None,
                "notes": None,
            })
    for cid in sorted(body_citations):
        if references and cid not in references:
            findings.append({
                "reference_id": f"ref-usage-missing-{cid:04d}",
                "reference_no": cid,
                "issue": "citation-without-reference-entry",
                "paragraph": None,
                "text": f"In-text citation [{cid}] has no numbered reference-list entry.",
                "review_status": "pending",
                "resolution": None,
                "revision": None,
                "notes": None,
            })
    return findings


def scan_text(text: str, source: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    formula_findings = formula_review_findings(lines)
    ref_usage_findings = reference_usage_findings(lines)
    section = ""
    claims: list[dict[str, Any]] = []
    paragraphs: list[dict[str, Any]] = []
    phrase_counts = Counter()
    marker_counts = Counter()
    paragraph_lengths: list[int] = []
    idx = 0

    for pno, line in enumerate(lines, 1):
        if not line:
            continue
        if line.startswith("摘要：") or line.startswith("摘要:"):
            section = "摘要"
        elif line.startswith("关键词：") or line.startswith("关键词:"):
            continue
        # Reference lists are bibliography metadata, not prose claims. Explicitly switch
        # sections even when the heading is plain DOCX text rather than Markdown/# syntax.
        if _is_reference_heading(line):
            section = "参考文献"
            continue
        new_section = infer_section(line, section)
        if new_section != section and (HEAD_RE.match(line) or line.startswith("#")):
            section = new_section
            continue
        if "参考文献" in section or section.lower() in {"references", "reference"}:
            continue

        # Paragraph-level cross-source metric check. This catches cases where adjacent
        # values are individually cited but use different metric definitions/populations
        # (e.g. one-way vs RTT, different datasets, different bandwidth assumptions).
        line_cits: list[int] = []
        for b in CIT_RE.findall(line):
            line_cits.extend(citation_ids(b))
        line_cits = sorted(set(line_cits))
        line_without_citations = CIT_RE.sub("", line)
        line_nums = [m.group(0).strip() for m in NUM_RE.finditer(line_without_citations) if re.search(r"\d", m.group(0))]
        line_metric_terms = [t for t in METRIC_TERMS if t.lower() in line.lower()]
        qualifier_pairs = [[a, b] for a, b in METRIC_QUALIFIER_PAIRS if a.lower() in line.lower() and b.lower() in line.lower()]
        cross_source_metric = len(line_cits) >= 2 and len(line_nums) >= 2 and bool(line_metric_terms) and bool(qualifier_pairs)

        clean_len = len(re.sub(r"\s+", "", line))
        paragraph_lengths.append(clean_len)
        for ph in AI_PHRASES:
            if ph in line:
                phrase_counts[ph] += line.count(ph)
        for mk in STRUCTURE_MARKERS:
            if mk in line:
                marker_counts[mk] += line.count(mk)

        enumerators = detect_enumerators(line)
        for fam, _, _ in enumerators:
            marker_counts[fam] += 1
        paragraphs.append({
            "paragraph": pno,
            "section": section or "<unsectioned>",
            "text": line,
            "length": clean_len,
            "enumerators": enumerators,
            "opener_template": normalized_paragraph_opener(line),
            "start_connector": paragraph_start_connector(line),
            "citations": line_cits,
            "numbers": line_nums,
            "metric_terms": line_metric_terms,
            "metric_qualifier_pairs": qualifier_pairs,
            "cross_source_metric": cross_source_metric,
        })

        sentences = [s.strip() for s in SENT_SPLIT_RE.split(line) if s.strip()]
        for sent in sentences:
            idx += 1
            cits: list[int] = []
            citation_blobs = CIT_RE.findall(sent)
            for b in citation_blobs:
                cits.extend(citation_ids(b))
            cits = sorted(set(cits))
            sent_without_citations = CIT_RE.sub("", sent)
            nums = [m.group(0).strip() for m in NUM_RE.finditer(sent_without_citations) if re.search(r"\d", m.group(0))]
            strong = [t for t in STRONG_TERMS if t in sent]
            causal = [t for t in CAUSAL_TERMS if t in sent]
            comp = [t for t in COMPARATIVE_TERMS if t in sent]
            generality = [t for t in GENERALITY_TERMS if t in sent]
            attribution_detected = bool(ATTRIBUTION_RE.search(sent))
            attribution_site_check = strong_attribution_site(sent, cits)
            tags: list[str] = []
            if nums:
                tags.append("numeric-claim")
            if strong:
                tags.append("strong-claim")
            if causal:
                tags.append("causal-claim")
            if comp:
                tags.append("comparative-claim")
            if len(cits) >= 3:
