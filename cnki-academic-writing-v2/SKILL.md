---
name: cnki-academic-writing-v2
description: Use for Chinese academic papers, literature reviews, course papers, reports, or research tasks that must ingest assignment requirements, search/verify CNKI literature when relevant, preserve evidence provenance, draft from verified evidence, run targeted precision/prose audits, and deliver in the supplied template. Do not use for casual web search or when the user explicitly says not to access CNKI.
---

# CNKI Academic Writing V2.7.3

V2.7.3 is a **targeted correctness patch** on V2.7. It preserves the simplified workflow and adds only checks that caught real defects in regression use. It keeps V2.7.2 formula/gate hardening and adds focused citation-attribution fidelity plus DOCX table-visibility checks. Do not add complexity merely to make the workflow look more auditable.

## 1. Hard rules

These rules are invariants:

1. Teacher/course requirements and the authoritative supplied template outrank skill defaults.
2. Never fabricate bibliographic data, paper-specific facts, numbers, methods, page locations, evidence, or access states.
3. Distinguish `metadata-only`, `abstract-verified`, and `fulltext-verified`; do not upgrade evidence level without actually obtaining and inspecting it.
4. A downloaded file is not evidence until it is parsed/read. A search hit is not an abstract review.
5. Images/scanned PDFs require real visual inspection when their contents matter. OCR/text geometry is not a substitute for claiming visual review.
6. Do not bypass CAPTCHA, login, subscription, paywall, or access-control restrictions.
7. Do not silently flatten or replace an authoritative DOCX template. Work on a copy.
8. Do not let prose polishing silently change citations, numbers, units, technical anchors, headings, conditions, or claim strength.
9. Do not call a precision audit complete because a citation merely exists. Important claims need a concrete evidence location and support note.
10. Do not call final Visual QA complete until the rendered pages were actually inspected.
11. Load each phase reference **before** doing that phase. Do not perform the work first and retroactively read the reference to claim compliance.
12. Internal consistency is not proof of theoretical correctness: any key equation that drives results, simulation, or conclusions must receive an independent formula-validity check.
13. For a complex/high-risk key equation, one self-contained re-derivation is not enough. Require **two structurally independent validation paths**; at least one path must differ in method from the original derivation (for example authoritative source, decision-region enumeration, numerical integration, or limiting/special-case check).
14. Bundled audit gates are mandatory when runnable. Do not replace `precise_audit.py scan/audit` or `layout_guard.py` with an informal “equivalent manual check”. Missing project ledgers are not a valid excuse for skipping `precise_audit.py scan`; the scan creates its own audit record. If a required script is technically unavailable or fails, record the exact failure and do not report that gate as passed.

Detailed policy is split into five files and should be loaded **only when that phase is reached**:

- `references/01-INTAKE-REQUIREMENTS.md`
- `references/02-RESEARCH-EVIDENCE.md`
- `references/03-AUDIT.md`
- `references/04-WRITING.md`
- `references/05-DELIVERY-QA.md`

Phase-loading order is simple: load `01` before requirement intake/contract work, `02` before research/evidence work, `03` before precision audit, `04` before prose polishing, and `05` before template/final-delivery/visual QA. A later retrospective read may help repair omissions, but it does not satisfy the intended execution order.

## 2. Requirement priority

Use this order:

1. teacher/rubric/submission rules/authoritative template;
2. user instructions for this paper;
3. supplied institutional conventions;
4. skill defaults.

If a missing field is safe to default, record the default and continue. Ask only for a genuinely blocking unknown. Preserve material conflicts instead of silently choosing.

For intake, policy layers, conflict handling, template recognition, images/scans, and requirement completeness, use `references/01-INTAKE-REQUIREMENTS.md`.

## 3. Project initialization

For a substantial project, initialize the standard records:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/provenance_ledger.py" init --root .
```

Typical project records live under:

```text
assignment/
references/
references/research/
papers/
draft/
delivery/
outputs/
```

Do not create records that are not useful for the current task.

If assignment files exist, ingest them before research:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/assignment_intake.py" ingest --root . --input "课程要求.pdf" "论文模板.docx"
```

`assignment_intake.py` is a parser/classifier, not an oracle. When it reports `needs_vision`, inspect the actual images/pages or keep the requirement unresolved.

## 4. Workflow configuration

If `assignment/workflow-config.json` exists, read it. Otherwise default to **MEDIUM** audit.

Audit levels remain:

- **LOW**: basic fact/citation safety for low-stakes work.
- **MEDIUM**: default; targeted important-claim review without full-corpus rereading.
- **HIGH**: deeper verification when the assignment or risk justifies it.

The selected level sets a minimum verification floor, not a quota. See `references/03-AUDIT.md`.

## 5. Research workflow

### Phase A — Build the assignment contract

Parse all requirement sources, resolve safe defaults, flag blocking unknowns, and identify the authoritative template before drafting. Use `references/01-INTAKE-REQUIREMENTS.md`.

### Phase B — Search CNKI

Use the bundled wrapper:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" search "检索词" --page 1 --output-limit 20 --return-fields search_basic
```

Reuse existing workspace/run IDs when possible. Search broadly enough to cover the assignment, but do not treat search breadth as a paper quota.

### Phase C — Fetch details and choose core literature

Fetch details in batches:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" fetch_details --workspace WORKSPACE --run RUN --top 20 --return-fields detail_full
```

Prefer sources that contribute a specific needed role: definition, method, comparison, data, limiting condition, engineering example, counterpoint, or recent status.

### Phase D — Expand evidence adaptively

Do **not** bulk-read every relevant paper. Expand to full text or a targeted section only when needed for:

- an important/high-risk claim;
- a missing limiting condition or comparison;
- a cross-source metric conflict;
- a required topic not supported at abstract level;
- a planned table/figure or explicit assignment requirement.

Use the smallest relevant page/section first. The goal is evidence sufficiency, not maximum reading volume. See `references/02-RESEARCH-EVIDENCE.md`.

### Phase E — Build a synthesis matrix

Before long-form drafting, organize claims by topic, source, evidence level, locator, role, and limits. Reuse this matrix instead of repeatedly rereading papers.

### Phase F — Draft from evidence

Draft against the assignment contract and synthesis matrix. Keep claims no stronger than their evidence. Separate source findings from your synthesis. Do not cite an example paper merely because it was supplied for formatting reference.

## 6. Evidence and citation rules

Use `references/02-RESEARCH-EVIDENCE.md` for backend commands, evidence budget, synthesis, and provenance details.

Minimum practical rules:

- exact numbers, sample sizes, methods, equations, thresholds, comparisons, and attributed conclusions need support that actually contains them;
- abstract-only evidence must not be described as full-text verification;
- a secondary citation should be identified when a source itself is quoting another work and the distinction matters;
- when sources use different definitions or directions (for example one-way vs round-trip delay), disclose the difference instead of forcing a direct comparison;
- if evidence is insufficient, soften/remove the claim or retrieve the minimum additional evidence needed.

## 7. Precision audit

Run a static scan on the draft/final candidate:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/precise_audit.py" scan --root . --input "delivery/final-audited.docx" --level auto
```

Then review only the required findings for the effective level.

For **high-risk / material-medium** claims, a positive `supported` verdict must include a concrete locator such as page, section, table, figure, or equivalent local source position plus a finding-specific note explaining what the evidence supports. A vague label such as `verified full text` is not enough.

Do not mechanically force the same strict locator rule onto every ordinary numeric claim in MEDIUM. The purpose is to catch important unsupported statements without turning the audit into a full-corpus reread.

Run the audit gate after review:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/precise_audit.py" audit --root . --level auto
```

For key numbered/derived equations that materially drive a result, verify two separate things:

- **formula syntax/structure**: balanced delimiters, complete function arguments, variable definitions, normalization/units, and no rendering damage;
- **theoretical validity**: independently validate the mathematics rather than merely checking implementation consistency.

For a **complex/high-risk** key equation (for example multi-threshold or piecewise decisions, multiple probability-tail terms, probability integrals/sums, nontrivial approximations, or formulas whose omitted event regions could change the result), require **two structurally independent validation paths**. A repeated algebraic derivation does not count twice. Valid second paths include an authoritative source, exhaustive decision-region/event enumeration, independent numerical integration, or a limiting/special-case check that would expose omitted terms. Record both paths in `verification_paths`.

A formula matching the code, CSV, table, and figure can still be wrong if all of them share the same mistaken equation. Implementation consistency is necessary, not sufficient.

The bundled precision scan and audit gate are mandatory when the scripts can run. Do not skip them because a manual audit was also performed or because no previous ledger exists. `scan` creates `references/research/precision-audit.json`; after required findings are reviewed, `audit` must be run and return `status: ok` before the precision gate is reported as passed. If the script cannot run, preserve the exact command/error and report the gate as unavailable rather than passed.

Also remove bibliography entries that are never cited in the paper unless the assignment explicitly requests a separate background bibliography.

For explicit source-attribution sentences such as `文献[n]指出/表明/证明…`, `已有研究…[n]`, `研究表明…[n]`, or `据/根据文献[n]…`, verify **citation fidelity at that exact citation site**. A real paper on the same topic is not enough; the cited source must support the proposition actually attributed to it.

For DOCX tables, treat a non-empty structured cell that becomes visually blank/invisible in the final rendering as a delivery defect. The precision scan performs a narrow static precheck for explicit white/hidden text; final rendered-page inspection remains authoritative.

For audit-level semantics, evidence sufficiency, cross-source metrics, structural findings, and failure states, use `references/03-AUDIT.md`.

## 8. Writing and anti-AI polish

After factual/citation auditing, scan prose:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" scan --root . --input "delivery/final-audited.docx" --level auto
```

Focus on high-value issues rather than rewriting everything: citation-led cadence, repetitive meta phrasing, empty academic filler, overloaded clauses, generic abstract/conclusion language, and audit-report-like prose.

Each required finding needs `review_status`, `resolution`, and a **finding-specific** `revision_note`. `keep` is valid. Reusing one boilerplate rationale across unrelated findings is a warning.

After targeted edits, protect factual invariants:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" guard --root . --before "delivery/final-audited.docx" --after "delivery/final.docx"
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" audit --root . --level auto
```

If the guard shows no citation/number/unit/technical-anchor/heading drift, do not reopen the whole literature set. Recheck only claims whose substance changed.

Do not add fake personal experience, deliberate mistakes, colloquial filler, or technical imprecision to imitate human writing. Stop when remaining edits are mainly taste-level.

See `references/04-WRITING.md` for detailed pattern policy.

## 9. Template, figures, tables, and final delivery

Use an authoritative DOCX template as the base whenever one is supplied. Preserve page setup, fixed cover elements, headers/footers, styles, numbering, tables, and required fields unless the assignment explicitly changes them.

Create figures/tables only when they add information. Do not add decorative visuals merely to make the paper look richer.

See `references/05-DELIVERY-QA.md`.

## 10. Final Visual QA

Render the final deliverable and inspect the pages. If baseline/final PDFs are available, run:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/layout_guard.py" --root . --before "delivery/final-audited.pdf" --after "delivery/final.pdf"
```

Before real page inspection, the guard must remain `needs_visual_review`. Automated page-count/text checks are review triggers only.

For papers ≤20 pages, inspect every final page. For longer papers, inspect first/last pages, all figure/table pages, edited regions, pagination-change regions, and a regular middle sample.

After **actual** human/vision-model inspection, rerun with:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/layout_guard.py" --root . --before "delivery/final-audited.pdf" --after "delivery/final.pdf" --visual-status passed --visual-note "逐页检查完成，无叠压/裁切/孤题等问题"
```

If issues were found, use `--visual-status issues_found` and fix only genuine layout defects. A sparse final reference page is not automatically wrong.

The visual pass should check overlap, clipping, broken table/figure continuation, orphan headings/captions/reference entries, abnormal trailing pages, title line breaks, footer/page-number integrity, and whether non-empty table cells are actually visible rather than white/hidden/background-colored.

## 11. Final pre-delivery check

Before handing over the paper:

1. run the requirement/template audit;
2. run precision audit at the configured level;
3. run prose guard/audit if prose was polished;
4. rerun the precision scan/audit on the **actual final DOCX** when factual content changed or when an old ledger may no longer match it;
5. render and complete real Visual QA;
6. confirm references/citations are continuous and no required deliverable is missing.

V2.7.3 intentionally does **not** use file hashes, visual manifests, evidence graphs, full-table OCR diffs, or heavy carry-forward state machines as mandatory gates. If the final DOCX changes, the lightweight safeguard is simple: audit the actual final file again.

## 12. Token-efficiency rules

- reuse search runs and saved structured records;
- fetch/detail/download in batches;
- read only the smallest relevant source slice for a flagged claim;
- do not repeatedly dump raw JSON into chat;
- do not repeatedly OCR/vision-review unchanged assignment files;
- do not reread every paper for final audit;
- keep prose edits local;
- stop when additional auditing is mostly cosmetic.

## 13. Failure handling

- **Unreadable image/scanned PDF**: do not guess; keep the requirement unresolved.
- **Template feature cannot be safely preserved**: keep the original copy and use a safer editing method if available; otherwise report the limitation.
- **Blocking requirement unknown**: ask only for the missing item that actually blocks delivery.
- **`captcha`**: stop repeated automation; do not bypass it.
- **`login_required` / `permission_denied`**: use legitimate access or fall back only when the assignment permits.
- **`format_mismatch` / `empty_body` / `source_app_invalid`**: do not mark full text verified.
- **CNKI unavailable**: do not fabricate results; clearly label any permitted alternative scholarly sources.

## 14. Final reporting

Do not collapse reading states into one misleading number. Prefer:

```text
Final references: N
abstract-verified only: A
fulltext-verified: F
  ├─ full read: X
  └─ targeted-section read: Y
Evidence-gap full-text additions: Z
Material formulas independently validated: K
Formula-syntax findings resolved: S
Reference-usage findings resolved: U
```

`fulltext-verified` describes evidence access/verification; it does not imply every page was read.
