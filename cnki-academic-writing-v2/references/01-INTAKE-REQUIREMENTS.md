# CNKI Academic Writing V2.7.3 — Intake Requirements


## Policy layers

## Purpose

Preserve a reliable quality floor for weaker agents without turning the Skill into a ceiling for stronger agents. The Skill therefore separates **invariants**, **default policies**, and **agent discretion**.

## Layer 1 — Invariants / hard constraints

These cannot be weakened, traded away, or silently overridden:

- explicit teacher/course requirements and current-task user instructions;
- source authenticity: no fabricated papers, authors, DOI, pages, data, methods, experiments, or conclusions;
- truthful evidence levels (`metadata-only`, `abstract-verified`, `fulltext-verified`);
- exact/paper-specific numerical claims require evidence at the level defined by the Skill;
- provenance for cited CNKI sources and honest handling of unavailable evidence;
- no bypass of CAPTCHA, login, permission, paywall, or other access controls;
- no claim that visual/scanned material was read unless it was actually inspected;
- authoritative template/format requirements when supplied;
- unresolved `blocking_unknown` items must not be silently guessed;
- the mandatory verification floor of the effective LOW/MEDIUM/HIGH audit level;
- safety and platform constraints.

Agent discretion never applies to these.

## Layer 2 — Default policies / guardrails

These are reliable fallbacks, **not quotas**. Examples:

- starting with roughly 3–6 focused search queries;
- using small targeted full-text expansion batches;
- using conventional academic structure when no structure is supplied;
- GB/T 7714 for Chinese coursework when no citation style is specified;
- clean A4 academic DOCX defaults when no template exists;
- moderate visual density such as a small number of useful tables/figures;
- MEDIUM when no audit level is selected;
- the normal phase ordering in `SKILL.md`;
- targeted audit and Evidence Gap behavior rather than brute-force rereading.

Words such as **normally**, **prefer**, **typical**, **reasonable**, **when useful**, and suggested numeric ranges usually identify this layer unless the surrounding rule explicitly marks them mandatory.

## Layer 3 — Agent discretion / optimization zone

A capable agent may depart from a default policy when the deviation is task-specific and likely to improve quality, efficiency, clarity, or delivery reliability. Examples:

- use 2 excellent queries instead of 6 redundant ones, or 9 diverse queries for a genuinely broad interdisciplinary topic;
- read an unusually high-value paper early because it is expected to support several planned claims, even before a literal gap is encountered;
- combine or reorder workflow steps when provenance and verification state remain intact;
- reorganize an outline around a stronger evidence-backed argument rather than a generic chapter template;
- omit suggested visuals when they add no information, or add an extra visual when it materially clarifies a complex mechanism;
- use a different parser/verification route when it is more reliable;
- perform extra targeted checks beyond the selected audit floor when cheap and useful.

## Conditions for a valid deviation

A material deviation is valid only if all apply:

1. **Concrete rationale** — tied to this task, source set, tool behavior, or evidence structure.
2. **Expected benefit** — quality, efficiency, evidence coverage, clarity, or reliability.
3. **No invariant violation** — explicit requirements and evidence-integrity rules remain intact.
4. **No audit downgrade** — the effective audit level's required floor is still completed.
5. **No brute-force substitution** — doing more work is not automatically better; relevance alone does not justify bulk full-text reading.

Do not ask the user for approval merely because a soft default is being changed. Ask only if the decision touches an explicit requirement, blocking unknown, safety/access boundary, or unresolved consequential preference.

## Material-decision record

Use `assignment/agent-decisions.json` only for deviations that materially affect research breadth, evidence strategy, structure, audit strategy, or delivery. Do not log routine micro-decisions.

Suggested shape:

```json
{
  "schema_version": "2.7",
  "decisions": [
    {
      "decision_id": "decision-001",
      "policy": "search_query_breadth",
      "layer": "default_policy",
      "default_behavior": "start with roughly 3-6 focused queries",
      "decision": "use 8 queries",
      "reason": "topic spans NTN architecture, mobility, routing and physical-layer Doppler, and the first queries showed low overlap",
      "expected_benefit": "better required-section coverage without increasing full-text reading",
      "constraints_checked": ["assignment requirements", "Adaptive Evidence Budget"],
      "status": "applied"
    }
  ]
}
```

An empty `decisions` array is valid when defaults were sufficient.

## Evidence-budget autonomy

Adaptive Evidence Budget remains the controlling principle. A strong agent does not need to wait until prose drafting exposes a literal gap; it may proactively read a source when it can name the **specific planned evidence contribution**.

Valid: `This paper is likely to provide the only real-world measurement evidence for the hardware-limitations section.`

Invalid: `This paper is relevant and downloadable.`

Full-text count remains an evidence ledger field, not a performance target.

## Audit-level autonomy

LOW/MEDIUM/HIGH define minimum coverage floors. The agent may perform additional targeted checks, but it may not self-downgrade or skip required checks. Explicit per-run or project audit settings remain authoritative.


## File intake

## Goal

Convert teacher/user-provided requirement files into auditable source records before research or drafting.

## Source roles

Assign one or more roles only when supported by context:

- `assignment_sheet`
- `rubric`
- `template`
- `example_paper`
- `required_reading`
- `other`

A filename containing “模板/template” is only a role hint, not proof of authority.

## Intake helper

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/assignment_intake.py" ingest --root . --input "要求.pdf" "模板.docx"
```

Useful options:

```text
--copy-sources          Copy source files into assignment/source-files/
--render-pdf-pages      Render PDF pages to PNG when possible
--max-render-pages N    Limit page rendering (default 20)
```

The helper writes `assignment/source-manifest.json` plus extracted text/metadata under `assignment/extracted/` and rendered pages under `assignment/rendered/`.

## Trust model

- Native DOCX XML text extraction: useful and deterministic, but still verify unusual text boxes/content controls visually when grading-critical.
- Native PDF text extraction: useful when substantial text is returned.
- Image or likely scanned PDF: `needs_vision: true`. It is not parsed until the actual image/page is visually inspected.
- OCR: transcription aid only. Verify grading-critical numbers and formatting from the image.

## Scanned PDF heuristic

The helper may mark a PDF `likely_scanned` when extracted text is absent or very sparse relative to page count. This is a heuristic, not proof.

## Requirement provenance

For hard constraints, record enough provenance to find the original statement again, e.g.:

```json
{
  "field": "word_count.min",
  "value": 3000,
  "source_ref": "src-0001",
  "locator": "PDF p.2 / visible line near heading ‘论文要求’",
  "confidence": "verified"
}
```

Do not cite OCR line numbers as exact if the OCR output was not visually verified.

## Example papers

Example/previous papers can inform structure and formatting, not factual claims or literature provenance. Their references remain unverified until independently retrieved.


## Course requirements

## Priority

Use this precedence for final deliverables:

1. teacher/course rubric, assignment sheet, supplied template, explicit submission rules;
2. user instructions for the current paper;
3. explicitly supplied institutional conventions;
4. skill defaults.

Evidence integrity and access-control boundaries are non-overridable.

## Requirements JSON

Recommended `assignment/requirements.json` shape:

```json
{
  "schema_version": "2.7",
  "status": "parsed",
  "source_notes": ["teacher rubric", "user prompt"],
  "hard_constraints": {
    "topic": null,
    "word_count": {"target": null, "min": null, "max": null},
    "required_sections": [],
    "reference_count": {"min": null, "max": null},
    "source_languages": [],
    "source_types_required": [],
    "source_types_forbidden": [],
    "date_range": {"from": null, "to": null},
    "citation_style": null,
    "format_template": null,
    "required_content": [],
    "ai_use_rules": null,
    "submission_format": null
  },
  "soft_preferences": {},
  "defaults_adopted": [],
  "unresolved": []
}
```

Only populate constraints actually supported by the assignment/user input. Do not convert a skill default into a fake teacher requirement.

## Defaults

If the assignment is silent, reasonable defaults may be adopted, for example:

- CNKI first for Chinese academic literature;
- recent literature emphasized for current-state discussion;
- GB/T 7714 for Chinese coursework when no other style is specified;
- a conventional academic structure appropriate to the task;
- enough references to support the argument without padding.

Record defaults under `defaults_adopted`.

## Conflict handling

When two supplied requirements conflict, prefer the more authoritative and more specific current-task source. Preserve the conflict in `unresolved` if it materially affects the deliverable. Do not silently choose a rule merely because it appears in this skill.


## File-derived requirement provenance (V2.5)

When requirements come from a photo/PDF/template/example, preserve source provenance instead of flattening everything into unattributed text. Recommended additional keys:

```json
{
  "source_notes": [
    {"source_ref": "src-0001", "role": "assignment_sheet", "review": "vision-reviewed"}
  ],
  "requirement_evidence": [
    {"field": "reference_count.min", "value": 8, "source_ref": "src-0001", "locator": "p.1", "confidence": "verified"}
  ]
}
```

If a file remains unreadable, put the affected field under `unresolved` rather than inferring it.


## Requirement completeness (V2.5.6)

After normalizing `requirements.json`, also create `assignment/requirement-completeness.json`. See `REQUIREMENT-COMPLETENESS.md`.

Do not treat missing teacher detail as a reason to reduce research/writing quality. Classify material fields as `confirmed`, `defaulted`, `blocking_unknown`, or `not_applicable`. Only `blocking_unknown` should interrupt the workflow. Safe defaults must be attributable to `skill_default`, not to the teacher/course.


## Requirement completeness

## Purpose

Sparse teacher instructions should not force low-quality writing or a long clarification interview. This layer separates what is known, what can be safely defaulted, and what genuinely blocks a reliable final submission.

The four statuses are:

- `confirmed`: explicitly supported by teacher/course material or current-task user instruction.
- `defaulted`: missing, but safely filled by a conservative academic default.
- `blocking_unknown`: cannot be safely defaulted and can materially invalidate the final deliverable.
- `not_applicable`: irrelevant to this task.

## Decision principle

Use explicit requirements when present. When silent, prefer a documented default over asking the user, unless the missing item is genuinely grading-critical or required for the requested submission artifact.

Do not infer hidden teacher preferences. Do not call a skill default a teacher requirement.

## Default matrix

| Field | If silent | Default behavior | Blocking? |
|---|---|---|---|
| Topic/title | Topic is known but exact title is not | Generate a precise working title and mark it `defaulted` | No |
| Topic/subject | No subject at all | Cannot research responsibly | Yes |
| Word/page count | No length rule | Choose a moderate length appropriate to task/paper type; record as skill default | No |
| Section structure | No required headings | Use a conventional academic structure driven by the question and evidence | No |
| Reference count | No minimum | Do not invent a quota; use evidence sufficiency | No |
| Citation style | No style | GB/T 7714 for Chinese coursework | No |
| Literature recency | No date range | Emphasize recent work for current-state sections; allow older foundational sources | No |
| Source language | No restriction | Use sources appropriate to topic; CNKI first for Chinese literature when relevant | No |
| Figures/tables | No count | Add only information-dense visuals that improve explanation/comparison | No |
| Formatting | No template/rule mentioned | Use clean A4 Chinese academic DOCX formatting | No |
| Submission format | No format | DOCX for editable delivery | No |
| Audit level | No setting | MEDIUM | No |
| Teacher/faculty template | Explicitly required but absent | Must obtain or clarify the template | Yes |
| Required dataset/case/reading | Explicitly referenced but absent | Must obtain or remove/clarify the requirement | Yes |
| AI-use policy | Explicit course policy is referenced but unavailable | Must obtain/clarify the rule before doing disallowed work | Yes |
| Conflicting authoritative rules | Conflict changes grading and cannot be resolved by authority/specificity | Human clarification required | Yes |
| Cover/signature/student fields | Submission-ready form requires unknown identity/course fields | Ask only for the missing fields or leave explicit placeholders if user permits | Usually yes for final submission |
| Deadline | Not needed to write the paper | Do not invent it | No |

## Moderate-length default

Do not convert the absence of a word count into a rigid universal quota. For an ordinary Chinese undergraduate course paper, a roughly 4,000–6,000 Chinese-character body is a reasonable *working default* when nothing else constrains length. Adjust upward/downward based on task complexity, supplied examples, required sections, and user instructions. Record the chosen target as `skill_default`.

For a graduation thesis, review, report, or other larger task, do not reuse the course-paper default mechanically. Use the task's actual structure and scope, and ask only if the missing length would materially affect submission correctness.

## Quality floor under sparse requirements

Sparse instructions do **not** relax:

- literature authenticity and provenance;
- full-text evidence rules;
- Adaptive Evidence Budget;
- Claim → Citation → Evidence precision audit;
- citation-bundle and cross-section consistency checks;
- structural AI-pattern review;
- technical accuracy and honest uncertainty.

## Required project record

Write `assignment/requirement-completeness.json`:

```json
{
  "schema_version": "2.7",
  "status": "assessed",
  "fields": [
    {
      "field": "topic",
      "status": "confirmed",
      "source": "teacher",
      "value": "低轨卫星互联网"
    },
    {
      "field": "citation_style",
      "status": "defaulted",
      "source": "skill_default",
      "value": "GB/T 7714",
      "reason": "assignment silent"
    },
    {
      "field": "reference_count",
      "status": "defaulted",
      "source": "skill_default",
      "value": "evidence-sufficiency; no fixed quota",
      "reason": "assignment silent"
    }
  ],
  "proceed_decision": "proceed",
  "blocking_unknowns": []
}
```

If blocking items exist:

```json
{
  "proceed_decision": "needs_user_input",
  "blocking_unknowns": [
    {
      "field": "format_template",
      "reason": "assignment explicitly requires the faculty DOCX template but it was not supplied"
    }
  ]
}
```

## Asking rule

Do not ask a checklist of every missing field. Ask only for the smallest information needed to resolve `blocking_unknown`. Continue automatically for `defaulted` items.
