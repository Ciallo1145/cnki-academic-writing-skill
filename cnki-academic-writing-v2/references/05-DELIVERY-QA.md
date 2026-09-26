# CNKI Academic Writing V2.7.3 — Delivery QA


## Template delivery

## Authority

A teacher-supplied template is an authoritative delivery source only to the extent it is current and not contradicted by a more explicit teacher instruction.

## Preferred strategy

1. Preserve the original template unchanged.
2. Copy it into `delivery/`.
3. Fill variable content in the copy.
4. Reuse existing paragraph/table styles whenever possible.
5. Preserve sections, headers/footers, fields, numbering, tables, content controls, and page setup.
6. Audit the final file against `assignment/template-spec.json` and the explicit assignment contract.

## Do not rebuild from blank unless necessary

Recreating a complex DOCX from scratch risks losing:

- section breaks;
- page numbers/field codes;
- hidden style dependencies;
- header/footer links;
- fixed cover tables;
- numbering definitions;
- content controls.

Use a blank recreation only when there is no editable template or the supplied template is technically unusable. Record that decision.

## Template spec

Recommended `assignment/template-spec.json` shape:

```json
{
  "schema_version": "2.5",
  "status": "selected",
  "source_ref": "src-0002",
  "source_path": ".../论文模板.docx",
  "delivery_strategy": "fill-template-copy",
  "page_setup": {},
  "styles": {},
  "fixed_elements": [],
  "placeholders": [],
  "required_fields": [],
  "notes": []
}
```

`template-candidates.json` is parser output; `template-spec.json` is the normalized authoritative plan after the model reviews the source and course requirements.

## Conflicts

Examples of conflicts that must be surfaced:

- PDF says “正文小四宋体” while the blank template body style is 五号宋体;
- assignment sheet says “APA 7” while the template contains a GB/T example reference;
- teacher says “不要封面” while the provided old template has one.

Prefer explicit current instruction over passive legacy formatting, and record the conflict.

## Final audit

Before delivery verify:

- file opens successfully;
- required cover/student fields are populated or intentionally left for the user;
- no placeholder tokens remain unintentionally;
- section order and headings match requirements;
- font/size/spacing/margins match authoritative rules;
- page numbering/header/footer behavior remains intact;
- references match required style and no numbered reference is left uncited unless a separate bibliography is explicitly required;
- if the assignment has a hard length range, verify the **final delivered DOCX** using the requested counting method; when the method is unspecified and the result is near a hard limit, record both a Chinese-character count and a Word-style count rather than declaring compliance from only the more favorable metric;
- no example-paper content was copied without independent justification.


## Figure and table policy

Use figures and tables only when they improve technical explanation, comparison, or evidence synthesis. They are not decoration.

## Authority

Explicit teacher/rubric/template requirements override all defaults below. If the teacher requires no figures, do not add them. If the teacher requires specific figures/tables, satisfy those requirements first.

## Default amount

When no explicit rule exists, a typical 3000–5000 Chinese-character course paper usually needs no more than about 1–2 useful tables and 0–2 necessary technical figures. This is a heuristic, not a quota. A paper may legitimately use none. Longer or experimental papers may need more.

## Preferred visual types

Prefer:

- self-created method-comparison tables;
- process diagrams or signal-processing pipelines;
- communication-system/block diagrams;
- method taxonomies or relationship diagrams;
- evidence-backed charts redrawn from verified values;
- tables summarizing verified literature with comparable conditions.

Avoid:

- decorative stock images;
- screenshots added merely to fill space;
- copying a paper figure when a simple self-created schematic would communicate the same idea;
- charts built from guessed or reconstructed numbers.

## Evidence rules

Every evidence-derived number must be traceable to a verified source. Exact paper-specific numbers normally require `fulltext-verified` support unless the exact value is present in verified abstract/detail metadata. Do not infer missing values from axes, prose, or nearby studies unless the task explicitly calls for an estimate and the estimate is labeled as such.

For multi-paper comparison tables/charts, expose relevant experimental context. Accuracy or similar metrics from different datasets, SNR ranges, channel models, sample populations, train/test protocols, or metric definitions are not directly comparable without qualification.

Useful context columns may include:

- source / row_id;
- dataset or scenario;
- signal/input representation;
- model/method;
- channel/SNR condition;
- metric definition;
- reported result;
- limitation / comparability note;
- evidence level.

## Captions and provenance

Every inserted visual should have:

- a figure/table number;
- a descriptive caption;
- an in-text reference and interpretation;
- source/provenance when evidence-derived.

For a self-created conceptual diagram based on the paper's synthesis, label it as self-drawn when appropriate and cite the supporting sources in the surrounding text or source note. For a redrawn chart/table based on literature values, cite the exact source(s).

## DOCX placement

Keep each figure/table near the paragraph that introduces and interprets it. Prefer the teacher template's existing caption/table styles. Do not break template pagination or fixed structures merely to force in a visual.


## Final visual QA

## Purpose

Text/citation checks cannot reliably see overlapping text, clipping, broken tables/figures, awkward pagination, or a nearly empty trailing page. Keep the rule simple:

> **Automated PDF checks may request visual review, but only an actual human or vision-capable model may mark visual review as passed.**

## Workflow

1. Keep the pre-polish rendered PDF when available.
2. Render the final DOCX to PDF.
3. Run the lightweight guard:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/layout_guard.py" `
  --root . `
  --before "delivery/final-audited.pdf" `
  --after "delivery/final.pdf"
```

Before page inspection, the expected result is `status: needs_visual_review` and `visual_review: not_completed`.

When `layout_guard.py` is runnable, do not skip it merely because pages were also inspected manually or by vision. The guard and the visual review serve different purposes: the guard records the delivery gate, while the human/vision inspection supplies the `visual_status`. If a pre-polish baseline is unavailable in an audit-only task, using the same rendered PDF as `--before` and `--after` is acceptable for establishing the gate record; still inspect the actual pages. If the script itself is unavailable/fails, record the exact failure and do not report `layout_guard: ok`.

4. Inspect the actual rendered pages with a human or vision-capable model. OCR/text extraction does not count as visual QA.
5. When the visual inspection is complete, rerun one of:

```powershell
# No visual defect found
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/layout_guard.py" `
  --root . --before "delivery/final-audited.pdf" --after "delivery/final.pdf" `
  --visual-status passed --visual-note "逐页检查完成，未发现叠压、裁切或孤儿页"

# Visual defect found
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/layout_guard.py" `
  --root . --before "delivery/final-audited.pdf" --after "delivery/final.pdf" `
  --visual-status issues_found --visual-note "第12页表格与正文发生遮挡"
```

No hash file, manifest, signature, or extra provenance object is required.

## Coverage floor

For papers of **20 pages or fewer**, inspect every final page after a prose/layout pass.

For longer papers, inspect at minimum:

- first two pages;
- last two pages;
- every figure/table page;
- known edited regions;
- pages around any page-count change;
- a regular sample through the middle.

## Table structure ↔ rendered visibility check

For final DOCX tables, do not assume that extracted/XML text is visible merely because it exists. On every inspected table page, confirm that cells which are structurally non-empty are visibly readable in the rendered page. Pay special attention to:

- white or near-background-colored text;
- hidden/vanished runs;
- font size effectively reduced to invisibility;
- clipped or overflowed cell text;
- cell content present in DOCX/XML but appearing blank in Word/PDF.

`precise_audit.py` performs a deliberately narrow static precheck for high-confidence explicit white/hidden text in non-empty DOCX cells. Treat those findings as review triggers, then confirm on the actual rendered page. Do not replace final visual inspection with OCR or XML-only checks.

## What to look for

- text overlap/collision;
- clipped text, figures, tables, captions, headers, or footers;
- broken table continuation;
- structurally non-empty table cells that render blank/invisible or blend into the background;
- orphaned heading/caption/reference item;
- avoidable sparse trailing page;
- bad title line breaks;
- abnormal blank space;
- page-number/footer problems;
- visibly broken equations: missing/mismatched brackets, clipped operators, damaged superscripts/subscripts, or incomplete function arguments.

Page-count drift or a sparse-tail warning is a **review trigger**, not proof that the document is wrong. Fix only real defects and prefer the least invasive template-safe adjustment.
