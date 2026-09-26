# CNKI Academic Writing V2.7.3 — Research Evidence


## Backend commands

The backend is `LongMarching/cnki-search-skill`, installed separately under `~/.agents/tools/cnki-search-skill-backend` by default.

Use the wrapper:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" --help
```

## Search

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" search "机器学习" --page 1 --output-limit 5 --return-fields search_basic
```

## Inspect an existing run

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" inspect --workspace WORKSPACE --run RUN --view rows --return-fields search_basic
```

## Fetch details

Prefer the supported group `detail_full` when complete detail metadata is needed:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" fetch_details --workspace WORKSPACE --run RUN --rows 1-5 --return-fields detail_full
```

Do not request unsupported `DOI` / `doi` return fields. Use citation export/full text as a DOI fallback only when the DOI is explicitly present.

## Export citations

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" export --workspace WORKSPACE --run RUN --rows 1-5 --mode GBTREFER BibTex
```

## Download

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/cnki_backend.py" download --workspace WORKSPACE --run RUN --rows 1-5 --format pdf --dir papers/cnki

`cnki_backend.py` resolves a relative `--dir` against the current course-paper project root before invoking the upstream backend. Use an absolute `--dir` only when the user explicitly wants storage outside the project. If the host cannot run commands from the project root, set `CNKI_PROJECT_ROOT` explicitly.
```

After download succeeds, verify and store the actual local path immediately. Later `inspect` output may not preserve `saved_to` / `filename` in every backend version.

## Common guarded states

- `captcha`
- `login_required`
- `permission_denied`
- `source_app_invalid`
- `empty_body`
- `format_mismatch`

Report them; do not bypass access controls.


## Optional parsers

`assignment_intake.py` has zero mandatory third-party Python dependencies for DOCX/XML and plain-text intake.

For richer PDF/image support it will opportunistically use:

- PyMuPDF (`fitz`) for PDF text extraction and page rendering;
- `pypdf` as a PDF text-extraction fallback;
- Poppler `pdftotext` / `pdftoppm` when available;
- Pillow for image dimensions.

These are optional. If unavailable, the script records `parser_unavailable` or `needs_vision` instead of inventing content. Codex may still inspect current conversation attachments or local rendered images with whatever native vision/file tools are available in its environment.


## Adaptive evidence budget

## Goal

Control full-text reading by **evidence sufficiency**, not by maximizing the number of papers and not by imposing a rigid cap tied to labels such as “course paper” or “graduation thesis”.

## Core rule

> Evidence sufficient → stop. Evidence gap → add the minimum targeted evidence.

A paper being relevant, recent, downloadable, or interesting is **not** enough reason to read it in full. A capable agent may nevertheless read a source proactively when it can name a specific planned evidence contribution before reading; this is agent discretion, not permission for bulk reading.

## Initial core set

After metadata/abstract screening, choose the smallest strong set that can cover the required technical sections and the most important claims. Prefer complementary coverage rather than many papers on the same narrow subtopic. One source may support several sections.

Do not start by downloading the entire shortlist.

## Coverage states

Track important claims/sections in the synthesis matrix with one of:

- `covered`: direct evidence is sufficient for the planned wording;
- `needs-triangulation`: direct evidence exists but an important comparison/limitation/contrasting result needs another source;
- `gap`: required content or a high-risk claim lacks adequate evidence;
- `optional-background`: useful context that does not justify more full-text reading.

## Valid triggers for more full text

The default is to add another full-text paper when at least one of the following applies. Under V2.5.6 layered policy, a capable agent may also act slightly earlier if it can state a concrete planned section/claim/comparison the source is expected to support:

1. a required section has a direct evidence gap;
2. a number, parameter, experiment, method detail, or strong claim needs exact support;
3. a comparison needs an independent/limiting/contradictory source;
4. a required method, scenario, population, time period, or viewpoint is missing;
5. the assignment/user explicitly requests broader full-text coverage.

Invalid trigger: “this paper is also relevant.”

The distinction is **specific evidence contribution vs. generic relevance**.

## Expansion protocol

Expand in small targeted batches, normally 1–3 papers for one named gap or tightly coupled planned evidence need. The 1–3 range is a default guardrail, not a hard cap. Before the batch, record:

```text
Evidence gap: ...
Why existing evidence is insufficient: ...
What the next paper must contribute: ...
```

After the batch, update the synthesis matrix and decide whether the gap is closed. Do not chain another bulk batch without reassessment.

## Stop rule

Stop full-text expansion when:

- every required substantive section has adequate direct evidence;
- numerical and high-risk claims are supported or softened/removed;
- important comparisons expose conditions and limitations;
- required source/type/date constraints are satisfied;
- remaining candidate papers are materially redundant for the paper being written.

Stop even if many relevant candidates remain.

## Long papers / graduation theses

There is no fixed low ceiling. A long thesis with many chapters, methods, comparisons, or a substantial literature-review requirement will naturally accumulate more evidence gaps and therefore more full-text sources. The same stop rule applies.

## Quality metric

`fulltext-verified` count is an evidence ledger field, **not a quality score**. Never read extra papers merely to raise this number.


## Evidence synthesis

## Purpose

The synthesis matrix prevents source-by-source paraphrase and helps the writer compare evidence before drafting.

Recommended `references/research/synthesis-matrix.json` shape:

```json
{
  "schema_version": "2.5.2",
  "claims": [
    {
      "claim_id": "claim-001",
      "section": "研究现状",
      "claim": "...",
      "supporting_sources": [
        {"source_ref": "cnki:row-0010", "evidence_level": "fulltext-verified"}
      ],
      "limiting_or_conflicting_sources": [],
      "comparability_notes": "",
      "coverage_state": "covered",
      "drafting_status": "supported",
      "wording_notes": ""
    }
  ]
}
```

## Rules

- Compare like with like: population, method, conditions, metrics, and time period matter.
- Do not label different contexts as contradictory without evidence.
- Record genuine limitations and conflicting results rather than smoothing them away.
- For important technical/numerical claims, prefer full-text evidence.
- Abstract evidence supports only what the abstract explicitly states.
- Official standards/documents/textbooks may be the right source for definitions or normative requirements even when they are not CNKI journal articles.
- A paper is not “core” merely because it is newest or has a prestigious-sounding title.


## Adaptive Evidence Budget

Use `coverage_state` to control further full-text reading. Only `gap`, `needs-triangulation`, or an explicit assignment requirement justifies adding full-text sources. `covered` items should not trigger more reading merely for completeness. See `ADAPTIVE-EVIDENCE-BUDGET.md`.


## Provenance schema

V2.5.6 preserves earlier records and adds explicit **reading scope** plus **final-use claim scope** so audit reports do not overstate what was actually read.

## `verified.json`

Recommended detailed record fields:

```json
{
  "schema_version": "2.7",
  "records": [
    {
      "id": "V14",
      "row_id": "row-0012",
      "workspace_id": "cws-...",
      "run_id": "run-...",
      "title": "...",
      "authors": "...",
      "source": "...",
      "date": "2026-09-20",
      "doi": null,
      "doi_status": "not_returned",
      "detail_status": "ok",
      "evidence_level": "abstract-verified",
      "used_in_final": true,
      "citation_number": 14,
      "intended_claims": [
        "40 h star-subpoint prediction peak error < 5 km",
        "mean error about 1 km"
      ],
      "claim_source_scope": "abstract",
      "local_fulltext_path": null
    }
  ],
  "papers": []
}
```

For a final-cited `abstract-verified` source, populate `intended_claims` and `claim_source_scope` (`abstract`, `details`, or `abstract+details`). This makes the allowed claim role explicit instead of forcing later auditors to infer it from the abstract again.

`used_in_final` / `citation_number` are recommended final-use annotations. V2.5.6 ledger validation checks `intended_claims` and `claim_source_scope` when either final-use marker is present.

## `fulltext-manifest.json` and detailed full-text records

```json
{
  "schema_version": "2.7",
  "papers": [
    {
      "row_id": "row-0010",
      "workspace_id": "cws-...",
      "run_id": "run-...",
      "title": "...",
      "download_status": "downloaded",
      "format": "PDF",
      "local_fulltext_path": "C:/.../paper.pdf",
      "file_exists_verified": true,
      "parse_verified": true,
      "read_verified": true,
      "read_scope": "full | targeted-sections",
      "read_scope_note": "full read / selected experiment and results sections",
      "page_count": 8,
      "evidence_level": "fulltext-verified"
    }
  ]
}
```

### Critical distinction

`fulltext-verified` means:

- the legitimate local full text exists;
- it parses;
- the evidence actually used was read and verified.

It **does not mean every page was read**. Use:

- `read_scope: full` for cover-to-cover/page-by-page reading;
- `read_scope: targeted-sections` for deliberate reading of only relevant sections/pages.

A 134-page thesis can legitimately be `fulltext-verified` with `targeted-sections` when all claims drawn from it are inside those reviewed sections.

Final reports should distinguish:

```text
fulltext-verified: F
full read: X
targeted-section read: Y
abstract-verified only: A
```

Do not report `F` as “阅读全文 F 篇” unless every one actually has `read_scope: full`.

## `precision-audit.json`

Generated by `precise_audit.py scan`, then completed by the Agent during targeted evidence review.

```json
{
  "schema_version": "2.7",
  "source": "delivery/final.docx",
  "claims": [
    {
      "claim_id": "claim-0001",
      "section": "7 结论",
      "text": "...",
      "citations": [12],
      "risk_tags": ["strong-claim", "evidence-sufficiency-review"],
      "risk_level": "high",
      "audit_status": "reviewed",
      "verdict": "supported",
      "evidence": [
        {
          "source_ref": "cnki:row-0013",
          "local_path": "papers/cnki/paper.pdf",
          "locator": "verified abstract",
          "support_note": "source itself uses consensus language"
        }
      ],
      "sufficiency_status": "reviewed",
      "sufficiency_verdict": "attribute-to-source",
      "revision": "文献[12]认为，跳波束正在成为重要方案……",
      "notes": "citation fidelity passed; single-source field-wide consensus wording was attributed"
    }
  ]
}
```

## Required invariants

- `metadata-only`: no abstract/full-text claim implied.
- `abstract-verified`: detail evidence was actually inspected.
- `fulltext-verified`: local file exists, parses, and the used evidence was actually read.
- `fulltext-verified` and `read_scope` are separate concepts.
- DOI is never inferred.
- Preserve `workspace_id`, `run_id`, `row_id` for cited CNKI sources.
- High-risk numeric/strong/comparative claims should include exact evidence locators when practical.
- A citation topic match is not enough: the cited evidence must support the proposition asserted.
- A faithful single-source citation is not automatically sufficient for an unattributed field-wide consensus/ranking claim.
- Cross-source values must use compatible metric definitions or explicitly disclose differences.
- Course requirements remain under `assignment/`; do not mix teacher rules into bibliographic provenance.

## Requirement completeness

`assignment/requirement-completeness.json` records whether each material requirement is `confirmed`, `defaulted`, `blocking_unknown`, or `not_applicable`. Final delivery should not proceed with unresolved blocking items.
