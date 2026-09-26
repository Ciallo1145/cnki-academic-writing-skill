#!/usr/bin/env python3
"""Lightweight post-render layout guard for academic DOCX delivery.

The guard only catches simple pagination regressions. It does not pretend to be a
vision model. Visual QA remains a separate explicit step: before that step is done,
status is ``needs_visual_review`` rather than ``ok``.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import median
from typing import Any

SCHEMA_VERSION = "2.7"


def pdf_page_count(path: Path) -> int:
    raw = path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page\b", raw))


def page_text_counts(path: Path) -> tuple[list[int] | None, str | None]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None, "pypdf unavailable; sparse-tail heuristic skipped"
    try:
        reader = PdfReader(str(path))
        counts = [len(re.sub(r"\s+", "", page.extract_text() or "")) for page in reader.pages]
        return counts, None
    except Exception as exc:
        return None, f"PDF text extraction failed; sparse-tail heuristic skipped: {exc}"


def compare(before: Path, after: Path, visual_status: str = "not_completed", visual_note: str | None = None) -> dict[str, Any]:
    b_pages = pdf_page_count(before)
    a_pages = pdf_page_count(after)
    automated_flags: list[str] = []
    warnings: list[str] = []
    review_reasons: list[str] = []

    if b_pages != a_pages:
        automated_flags.append(f"rendered page count changed: {b_pages} -> {a_pages}")
        review_reasons.append("page-count-drift")

    counts, note = page_text_counts(after)
    sparse_tail = False
    tail_detail: dict[str, Any] | None = None
    if counts:
        nonzero = [x for x in counts[:-1] if x > 0]
        baseline = median(nonzero) if nonzero else 0
        last = counts[-1]
        threshold = max(180, int(baseline * 0.22)) if baseline else 180
        if len(counts) >= 2 and last < threshold:
            sparse_tail = True
            tail_detail = {
                "last_page_text_chars": last,
                "median_previous_page_text_chars": baseline,
                "threshold": threshold,
            }
            automated_flags.append("final rendered page is unusually sparse; visually check for orphaned references/paragraphs or avoidable pagination")
            review_reasons.append("sparse-final-page")

    inspect_all = a_pages <= 20
    mandatory_pages = list(range(1, a_pages + 1)) if inspect_all else sorted(set([1, 2, max(1, a_pages - 1), a_pages]))

    if visual_status == "not_completed":
        status = "needs_visual_review"
    elif visual_status == "issues_found":
        status = "warning"
        warnings.append("visual review found page-level issue(s); fix and re-render before final delivery")
    else:  # passed
        # Page-count/sparse-tail findings are review triggers, not permanent failures.
        # A real visual review may legitimately confirm that the layout is acceptable.
        status = "ok"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "before": str(before),
        "after": str(after),
        "baseline_page_count": b_pages,
        "final_page_count": a_pages,
        "page_count_changed": b_pages != a_pages,
        "final_page_text_chars": counts,
        "sparse_final_page": sparse_tail,
        "sparse_final_page_detail": tail_detail,
        "visual_review": visual_status,
        "visual_review_scope": "all-pages" if inspect_all else "sample-plus-changed-regions",
        "mandatory_visual_pages": mandatory_pages,
        "visual_review_note": visual_note,
        "review_reasons": review_reasons,
        "automated_flags": automated_flags,
        "warnings": warnings,
        "note": note or "Automated checks are only a regression aid. Mark visual_review=passed only after a human or vision-capable model actually inspects the rendered pages.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare rendered PDFs after prose/layout changes")
    ap.add_argument("--root", default=".")
    ap.add_argument("--before", required=True, help="baseline rendered PDF")
    ap.add_argument("--after", required=True, help="final rendered PDF")
    ap.add_argument("--visual-status", choices=["not_completed", "passed", "issues_found"], default="not_completed", help="set only after actual rendered-page inspection")
    ap.add_argument("--visual-note", default=None, help="short note from the actual visual review")
    ap.add_argument("--json-out", default="references/research/layout-guard.json")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    before = Path(args.before).expanduser()
    after = Path(args.after).expanduser()
    if not before.is_absolute():
        before = root / before
    if not after.is_absolute():
        after = root / after
    if not before.exists() or not after.exists():
        missing = [str(x) for x in (before, after) if not x.exists()]
        print(json.dumps({"status": "warning", "warnings": [f"missing rendered PDF: {x}" for x in missing]}, ensure_ascii=False, indent=2))
        return 1

    result = compare(before.resolve(), after.resolve(), args.visual_status, args.visual_note)
    out = Path(args.json_out).expanduser()
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
