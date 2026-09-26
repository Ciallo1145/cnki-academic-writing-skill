#!/usr/bin/env python3
"""Evidence-safe prose polish helper for Chinese academic writing.

This helper does not rewrite prose. It identifies a small set of high-value wording
and cadence targets, then verifies that a later polish pass did not silently change
citations, quantitative facts, technical anchors, or section headings.

Supported inputs: .docx, .md, .txt. No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SCHEMA_VERSION = "2.7"
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CIT_RE = re.compile(r"\[(\d+(?:\s*[-–—]\s*\d+)?(?:\s*[,，]\s*\d+(?:\s*[-–—]\s*\d+)?)*)\]")
NUM_RE = re.compile(r"(?<![A-Za-z])[-−]?\d+(?:\.\d+)?\s*(?:%|％|dB|db|ms|s|秒|分钟|min|h|小时|M|K|GB|MB|Gb/s|Mb/s|kbit/s|MHz|GHz|kHz|Hz|km/s|km|m|倍|个百分点|类|层|头|个|篇|页|万|亿)?")
ACRONYM_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}[A-Z0-9]*(?:/[A-Z0-9]{2,})*|\dGPP|\dG|[A-Z]+\d+(?:\.\d+)?)(?![A-Za-z0-9])")
HEAD_RE = re.compile(r"^(?:#{1,6}\s+.+|\d+(?:\.\d+)*\s+.+|[一二三四五六七八九十]+[、.]\s*.+|摘要\s*[:：]?|结论\s*[:：]?|参考文献\s*[:：]?)$")
SENT_SPLIT_RE = re.compile(r"(?<=[。！？；;])")
SOURCE_LED_RE = re.compile(r"^(?:文献\s*\[[^\]]+\]|研究\[[^\]]+\]|[^，。；;]{1,18}等(?:认为|指出|提出|发现|报告|给出))")

META_PHRASES = [
    "需要说明的是", "值得注意的是", "需要指出的是", "可以看出", "由此可见",
    "综上所述", "总体来看", "总体而言", "不难发现", "分析表明", "可以发现",
]
FILLER_PHRASES = [
    "具有重要意义", "具有重要的理论意义", "具有重要的现实意义", "具有广阔的应用前景",
    "提供一定参考", "提供参考", "具有一定借鉴意义", "奠定坚实基础", "进一步推动",
    "助力", "赋能", "值得进一步研究", "值得深入研究",
]


def read_docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        raw = z.read("word/document.xml")
    root = ET.fromstring(raw)
    body = root.find(f"{W_NS}body")
    if body is None:
        return []
    blocks: list[str] = []
    for node in body:
        if node.tag == f"{W_NS}p":
            texts = [t.text or "" for t in node.iter(f"{W_NS}t")]
            s = "".join(texts).strip()
            if s:
                blocks.append(s)
        elif node.tag == f"{W_NS}tbl":
            for tr in node.iter(f"{W_NS}tr"):
                cells: list[str] = []
                for tc in tr.findall(f"{W_NS}tc"):
                    ts = [t.text or "" for t in tc.iter(f"{W_NS}t")]
                    c = "".join(ts).strip()
                    if c:
                        cells.append(c)
                if cells:
                    blocks.append(" | ".join(cells))
    return blocks


def read_paragraphs(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        return read_docx_paragraphs(path)
    return [x.strip() for x in path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n").split("\n") if x.strip()]


def infer_section(line: str, current: str) -> str:
    s = line.strip()
    if s.startswith("摘要：") or s.startswith("摘要:"):
        return "摘要"
    if HEAD_RE.match(s) and len(s) <= 100:
        return s.lstrip("# ")
    return current


def add_finding(findings: list[dict[str, Any]], *, section: str, kind: str, severity: str, paragraphs: list[int], snippets: list[str], reason: str, recommendation: str, metrics: dict[str, Any] | None = None) -> None:
    findings.append({
        "polish_id": f"polish-{len(findings)+1:04d}",
        "section": section,
        "pattern_type": kind,
        "severity": severity,
        "paragraphs": paragraphs,
        "snippets": snippets[:5],
        "reason": reason,
        "recommendation": recommendation,
        "metrics": metrics or {},
        "review_status": "pending",
        "resolution": None,
        "revision_note": None,
    })


def scan(path: Path) -> dict[str, Any]:
    paras = read_paragraphs(path)
    section = "<unsectioned>"
    records: list[dict[str, Any]] = []
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for i, line in enumerate(paras, 1):
        new_sec = infer_section(line, section)
        is_heading = new_sec != section and HEAD_RE.match(line.strip()) is not None
        if new_sec != section:
            section = new_sec
        if is_heading or line.replace(" ", "") in {"参考文献", "参考资料"}:
            continue
        if "参考文献" in section:
            continue
        sentences = [x.strip() for x in SENT_SPLIT_RE.split(line) if x.strip()]
        source_led = [s for s in sentences if SOURCE_LED_RE.search(s)]
        meta_hits = [p for p in META_PHRASES if p in line]
        filler_hits = [p for p in FILLER_PHRASES if p in line]
        rec = {
            "paragraph": i,
            "section": section,
            "text": line,
            "char_len": len(re.sub(r"\s+", "", line)),
            "sentence_count": len(sentences),
            "source_led_count": len(source_led),
            "citation_count": len(CIT_RE.findall(line)),
            "meta_hits": meta_hits,
            "filler_hits": filler_hits,
        }
        records.append(rec)
        by_section[section].append(rec)

    findings: list[dict[str, Any]] = []

    # 1. Citation-led cadence: several sentences in one paragraph read as a literature ledger.
    for r in records:
        if r["source_led_count"] >= 2 and r["citation_count"] >= 2:
            sev = "high" if r["source_led_count"] >= 3 else "medium"
            add_finding(
                findings, section=r["section"], kind="citation-led-cadence", severity=sev,
                paragraphs=[r["paragraph"]], snippets=[r["text"]],
                reason="Multiple sentences are led by source labels, which can make the paragraph read like evidence inventory rather than topic-driven synthesis.",
                recommendation="Keep the citations, but lead with the technical point and attach sources to the propositions they support. Do not merge incompatible evidence.",
                metrics={"source_led_sentences": r["source_led_count"], "citation_groups": r["citation_count"]},
            )

    # 2. Neighboring source-led paragraph run.
    for sec, rs in by_section.items():
        run: list[dict[str, Any]] = []
        for r in rs + [{"source_led_count": 0}]:
            if r.get("source_led_count", 0) >= 1:
                run.append(r)
            else:
                if len(run) >= 3:
                    add_finding(
                        findings, section=sec, kind="source-led-paragraph-run", severity="medium",
                        paragraphs=[x["paragraph"] for x in run], snippets=[x["text"] for x in run],
                        reason="Three or more neighboring paragraphs are organized around source names rather than the argument/topic.",
                        recommendation="Reorganize only if it improves flow: group evidence by mechanism, condition, contrast, or conclusion while preserving source attribution.",
                        metrics={"run_length": len(run)},
                    )
                run = []

    # 3. Repeated meta/caveat phrases in one section.
    for sec, rs in by_section.items():
        counts = Counter(p for r in rs for p in r["meta_hits"])
        for phrase, count in counts.items():
            if count >= 3:
                selected = [r for r in rs if phrase in r["meta_hits"]]
                add_finding(
                    findings, section=sec, kind="repeated-meta-phrase", severity="medium",
                    paragraphs=[r["paragraph"] for r in selected], snippets=[r["text"] for r in selected],
                    reason=f"The meta phrase '{phrase}' repeats {count} times in one section and may create an audit-report cadence.",
                    recommendation="Keep the caveat itself, but integrate it directly into the technical sentence or vary the transition where natural.",
                    metrics={"phrase": phrase, "count": count},
                )

    # 4. Empty/low-information academic filler. Single hits are low; repeated section hits become medium.
    for sec, rs in by_section.items():
        hits = [(r, p) for r in rs for p in r["filler_hits"]]
        if not hits:
            continue
        if len(hits) >= 3:
            add_finding(
                findings, section=sec, kind="filler-density", severity="medium",
                paragraphs=sorted({r["paragraph"] for r, _ in hits}), snippets=[r["text"] for r, _ in hits],
                reason="Several low-information academic filler phrases appear in the same section.",
                recommendation="Delete or replace only where the sentence contributes no concrete technical content; retain wording that carries a real limitation or implication.",
                metrics={"hits": [p for _, p in hits]},
            )
        else:
            for r, phrase in hits:
                add_finding(
                    findings, section=sec, kind="filler-phrase", severity="low",
                    paragraphs=[r["paragraph"]], snippets=[r["text"]],
                    reason=f"Potentially low-information phrase: '{phrase}'.",
                    recommendation="Review in context. Keep if it carries a specific implication; otherwise tighten or delete it.",
                    metrics={"phrase": phrase},
                )

    # 5. Clause-heavy long sentence. Threshold intentionally conservative.
    for r in records:
        if r["char_len"] < 150:
            continue
        clause_count = len(re.findall(r"[，,；;：:]", r["text"])) + 1
        if clause_count < 6:
            continue
        sev = "medium" if (r["char_len"] >= 280 and clause_count >= 10) else "low"
        add_finding(
            findings, section=r["section"], kind="clause-overload", severity=sev,
            paragraphs=[r["paragraph"]], snippets=[r["text"]],
            reason="A long sentence carries many clauses, conditions, or evidence items, which may hurt readability even when factually correct.",
            recommendation="Split only at a semantic boundary. Preserve all conditions, citations, numbers, and attribution strength.",
            metrics={"chars": r["char_len"], "estimated_clauses": clause_count},
        )

    summary = Counter(f["severity"] for f in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": str(path),
        "summary": {
            "polish_findings": len(findings),
            "high": summary.get("high", 0),
            "medium": summary.get("medium", 0),
            "low": summary.get("low", 0),
        },
        "polish_findings": findings,
    }


def load_level(root: Path, requested: str) -> str:
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


def required(f: dict[str, Any], level: str) -> bool:
    sev = f.get("severity", "low")
    if level == "low":
        return sev == "high"
    if level == "medium":
        return sev in {"high", "medium"}
    return True


def write_scan_report(data: dict[str, Any], path: Path, level: str) -> None:
    q = [f for f in data["polish_findings"] if required(f, level)]
    s = data["summary"]
    lines = [
        "# Evidence-Safe Prose Polish Queue", "",
        f"Source: `{data['source']}`", f"Level: `{level}`", "",
        f"- Findings: {s['polish_findings']} (high {s['high']} / medium {s['medium']} / low {s['low']})",
        f"- Required by level: {len(q)}", "",
        "> These are wording/cadence targets, not proof of AI authorship and not automatic rewrite instructions.",
        "> Every reviewed finding should have a finding-specific `revision_note`; do not reuse one boilerplate rationale across unrelated patterns.", "",
    ]
    for f in q:
        lines += [
            f"## {f['polish_id']} · {f['severity'].upper()} · {f['section']}", "",
            f"- pattern: {f['pattern_type']}",
            f"- paragraphs: {f['paragraphs']}",
            f"- reason: {f['reason']}",
            f"- recommendation: {f['recommendation']}",
            f"- metrics: {json.dumps(f['metrics'], ensure_ascii=False)}", "",
        ]
        for snip in f.get("snippets", [])[:3]:
            lines.append(f"> {snip}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_protected(path: Path) -> dict[str, Counter[str] | list[str]]:
    paras = read_paragraphs(path)
    text = "\n".join(paras)
    citations = Counter(re.sub(r"\s+", "", m.group(0)) for m in CIT_RE.finditer(text))
    number_text = CIT_RE.sub("", text)
    numbers = Counter(re.sub(r"\s+", "", m.group(0)) for m in NUM_RE.finditer(number_text) if re.search(r"\d", m.group(0)))
    acronyms = Counter(m.group(0) for m in ACRONYM_RE.finditer(text))
    headings = [p.strip() for p in paras if HEAD_RE.match(p.strip()) and len(p.strip()) <= 100]
    return {"citations": citations, "numbers": numbers, "technical_anchors": acronyms, "headings": headings}


def counter_delta(a: Counter[str], b: Counter[str]) -> dict[str, dict[str, int]]:
    keys = sorted(set(a) | set(b))
    out: dict[str, dict[str, int]] = {}
    for k in keys:
        if a[k] != b[k]:
            out[k] = {"before": a[k], "after": b[k]}
    return out


def guard(before: Path, after: Path) -> dict[str, Any]:
    b = extract_protected(before)
    a = extract_protected(after)
    changes = {
        "citations": counter_delta(b["citations"], a["citations"]),  # type: ignore[arg-type]
        "numbers": counter_delta(b["numbers"], a["numbers"]),  # type: ignore[arg-type]
        "technical_anchors": counter_delta(b["technical_anchors"], a["technical_anchors"]),  # type: ignore[arg-type]
        "headings_changed": b["headings"] != a["headings"],
        "headings_before": b["headings"],
        "headings_after": a["headings"],
    }
    warnings: list[str] = []
    if changes["citations"]:
        warnings.append("citation tokens changed during prose polish")
    if changes["numbers"]:
        warnings.append("numeric/unit tokens changed during prose polish")
    if changes["technical_anchors"]:
        warnings.append("technical acronym/anchor tokens changed during prose polish")
    if changes["headings_changed"]:
        warnings.append("section headings/order changed during prose polish")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if not warnings else "warning",
        "before": str(before),
        "after": str(after),
        "warnings": warnings,
        "changes": changes,
        "note": "A warning is a review trigger, not automatic proof of damage. Intentional evidence-backed corrections must be documented outside the prose-only pass.",
    }


def cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    inp = Path(args.input).expanduser()
    if not inp.is_absolute():
        inp = root / inp
    effective = load_level(root, args.level)
    data = scan(inp.resolve())
    data["effective_level"] = effective
    jout = Path(args.json_out).expanduser()
    mout = Path(args.md_out).expanduser()
    if not jout.is_absolute():
        jout = root / jout
    if not mout.is_absolute():
        mout = root / mout
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_scan_report(data, mout, effective)
    print(json.dumps({"status": "ok", "level": effective, "json": str(jout.resolve()), "markdown": str(mout.resolve()), **data["summary"], "required_by_level": sum(1 for f in data["polish_findings"] if required(f, effective))}, ensure_ascii=False, indent=2))
    return 0


def normalize_rationale(text: str) -> str:
    """Normalize review rationale for duplicate-boilerplate detection."""
    text = re.sub(r"\s+", "", text or "")
    text = re.sub(r"[，。；;：:、,.!?！？（）()【】\[\]`'\"]", "", text)
    return text


def cmd_audit(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    p = Path(args.file).expanduser()
    if not p.is_absolute():
        p = root / p
    data = json.loads(p.read_text(encoding="utf-8"))
    effective = load_level(root, args.level)
    pending: list[str] = []
    warnings: list[str] = []
    required_count = 0
    required_reviewed = 0
    total_reviewed = 0
    required_revised = required_kept = required_na = 0
    total_revised = total_kept = total_na = 0
    rationale_groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for f in data.get("polish_findings", []):
        is_required = required(f, effective)
        if is_required:
            required_count += 1
        reviewed = f.get("review_status") == "reviewed" and f.get("resolution") in {"keep", "revised", "not-applicable"}
        if is_required and not reviewed:
            pending.append(str(f.get("polish_id")))
            continue
        if not reviewed:
            continue

        total_reviewed += 1
        if is_required:
            required_reviewed += 1
        res = f.get("resolution")
        if res == "revised":
            total_revised += 1
            if is_required: required_revised += 1
        elif res == "keep":
            total_kept += 1
            if is_required: required_kept += 1
        else:
            total_na += 1
            if is_required: required_na += 1

        note = str(f.get("revision_note") or "").strip()
        if len(note) < 8:
            warnings.append(f"{f.get('polish_id')}: reviewed finding needs a finding-specific rationale in revision_note")
        else:
            rationale_groups[normalize_rationale(note)].append({
                "id": str(f.get("polish_id")),
                "pattern": str(f.get("pattern_type")),
                "section": str(f.get("section")),
            })

    duplicate_rationale_groups: list[dict[str, Any]] = []
    for norm, items in rationale_groups.items():
        patterns = sorted({x["pattern"] for x in items})
        if norm and len(items) >= 3 and len(patterns) >= 2:
            duplicate_rationale_groups.append({"count": len(items), "patterns": patterns, "ids": [x["id"] for x in items]})
            warnings.append(
                f"boilerplate rationale repeated for {len(items)} reviewed findings across {len(patterns)} pattern types; "
                "record finding-specific keep/revise reasons"
            )

    summary = {
        "level": effective,
        "total_findings": len(data.get("polish_findings", [])),
        "required": required_count,
        "required_reviewed": required_reviewed,
        "optional_reviewed": total_reviewed - required_reviewed,
        "total_reviewed": total_reviewed,
        "pending": len(pending),
        "required_revised": required_revised,
        "required_keep": required_kept,
        "required_not_applicable": required_na,
        "revised": total_revised,
        "keep": total_kept,
        "not_applicable": total_na,
        "duplicate_rationale_groups": duplicate_rationale_groups,
    }
    data["schema_version"] = SCHEMA_VERSION
    data["polish_execution_summary"] = summary
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "ok" if not pending and not warnings else "warning",
        **summary,
        "pending_ids": pending,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


def cmd_guard(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    before = Path(args.before).expanduser(); after = Path(args.after).expanduser()
    if not before.is_absolute(): before = root / before
    if not after.is_absolute(): after = root / after
    result = guard(before.resolve(), after.resolve())
    if args.json_out:
        out = Path(args.json_out).expanduser()
        if not out.is_absolute(): out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Evidence-safe targeted prose polish scan and invariant guard")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scan", help="create a small high-value prose-polish queue")
    s.add_argument("--root", default=".")
    s.add_argument("--input", required=True)
    s.add_argument("--level", choices=["auto", "low", "medium", "high"], default="auto")
    s.add_argument("--json-out", default="references/research/prose-polish.json")
    s.add_argument("--md-out", default="references/cnki/prose-polish.md")
    a = sub.add_parser("audit", help="verify required polish findings were reviewed")
    a.add_argument("--root", default=".")
    a.add_argument("--file", default="references/research/prose-polish.json")
    a.add_argument("--level", choices=["auto", "low", "medium", "high"], default="auto")
    g = sub.add_parser("guard", help="compare audited pre-polish and post-polish drafts for protected-token drift")
    g.add_argument("--root", default=".")
    g.add_argument("--before", required=True)
    g.add_argument("--after", required=True)
    g.add_argument("--json-out", default="references/research/prose-guard.json")
    args = p.parse_args()
    if args.command == "scan": return cmd_scan(args)
    if args.command == "audit": return cmd_audit(args)
    return cmd_guard(args)


if __name__ == "__main__":
    raise SystemExit(main())
