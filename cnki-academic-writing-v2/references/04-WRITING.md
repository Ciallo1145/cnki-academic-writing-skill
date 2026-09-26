# CNKI Academic Writing V2.7.3 — Writing


## Structural AI-pattern review

## Purpose

This policy reviews **mechanical writing structure**, not authorship. A structural hit is never proof that text was written by AI. The goal is to find passages that feel over-organized, repetitive, or template-driven and decide whether they should be kept or rewritten.

Do not build an endless blacklist of words. Single words such as `首先`, `其一`, `此外`, or `因此` are normal academic Chinese. The relevant signal is **pattern density and repetition across neighboring paragraphs or within one section**.

## Patterns worth reviewing

### 1. Ordered prose enumeration

Examples:

- `其一… 其二… 其三… 其四…`
- `第一… 第二… 第三…`
- `一是… 二是… 三是…`
- `首先… 其次… 再次… 最后…`

A sequence of three is a review target. Four or more in one prose section is a stronger target. Keep it when the content genuinely needs a numbered taxonomy; rewrite when the sequence exists mainly to make the section look tidy.

### 2. Repeated paragraph-opening templates

Review when three or more paragraphs begin with the same grammatical shell, for example:

- `从……层面看……`
- `在……场景下……`
- `对于……而言……`
- repeated ordinal openings with only the noun phrase changed.

The problem is not the phrase itself; it is a long run of mechanically parallel openings.

### 3. Connector-start density

If many neighboring paragraphs begin with discourse connectors such as `此外 / 同时 / 另一方面 / 因此 / 进一步`, inspect the section for forced transitions. Do not remove connectors mechanically.

### 4. Over-symmetric paragraph length

Very uniform paragraph lengths across a section can be a weak signal of templated drafting. Treat it as low-priority only. Never rewrite solely because lengths are similar.

### 5. Repeated rhetorical skeleton

During model review, look beyond lexical matches. Examples include several consecutive paragraphs that all follow a pattern like:

`提出对象 → 列优点 → 加一句“但” → 给局限 → 因此总结`

or every subsection ending with the same style of summary sentence.

The static scanner can only approximate this. The model should inspect flagged neighboring paragraphs together.

## Review outcomes

For each `style_findings` item in `references/research/precision-audit.json`, record:

```json
{
  "style_id": "style-0001",
  "review_status": "reviewed",
  "resolution": "keep | revised | not-applicable",
  "notes": "why this structure is acceptable or what was changed"
}
```

Use `keep` when the structure genuinely improves technical clarity. Use `revised` when the passage was mechanically repetitive and was varied without weakening technical precision. Use `not-applicable` for false positives.

## Audit-level behavior

- **LOW:** review only high-severity structural findings.
- **MEDIUM:** review high + medium findings.
- **HIGH:** review all structural findings, including weak symmetry signals.

Structural review must remain targeted. Do not regenerate an entire paper merely to make it look less AI-written.

## Important boundary

Never introduce fake personal experience, fake experiments, fake mistakes, colloquial filler, or technical imprecision to imitate human writing. Naturalness comes from concrete content, varied but purposeful structure, and evidence-aware wording.


## Evidence-safe prose polish

## Purpose

This pass improves **readability, natural Chinese academic prose, paragraph rhythm, and student-level voice** after factual/evidence auditing is already complete.

It is not a second research phase and not a whole-paper paraphrasing pass. The default is **targeted refinement of high-value passages**.

The governing rule is:

> **The prose layer may improve expression, but it has no authority to silently alter the evidence layer.**

## Protected content during prose-only polishing

Unless a separate evidence audit explicitly authorizes a correction, prose polishing must preserve:

- citation identities and citation-to-claim attachment;
- numbers, units, ranges, percentages, dates, sample sizes, parameters, and metrics;
- technical conditions such as dataset, SNR, channel, orbit altitude, frequency band, minimum elevation angle, population, and evaluation protocol;
- source attribution (`文献[X]认为/指出…`) and the strength/breadth of the original claim;
- caveats, limitations, uncertainty, and cross-source comparability warnings;
- technical terms, acronyms, standards, model names, system names, and named methods;
- heading hierarchy and assignment-required structure.

Do not upgrade `可能/部分/在该条件下` into stronger language merely because the stronger sentence reads better.

## High-value polish targets

### 1. Citation-led prose

A review paper can become a literature ledger when too many sentences begin with `文献[X]指出/提出/认为`.

Prefer topic-driven synthesis when safe:

- first state the technical relation/mechanism/contrast;
- place citations directly after the proposition each source supports;
- retain explicit attribution when the statement is an author judgment rather than an established fact.

Do **not** merge sources with incompatible conditions merely to make the prose smoother.

### 2. Evidence-display cadence

A paragraph that simply presents number A, number B, number C may be correct but still read like an audit report. Organize evidence around a point:

`technical point → evidence/conditions → interpretation/limitation`

Do not invent a stronger conclusion to create narrative flow.

### 3. Repeated caveat/meta phrases

Phrases such as `需要说明的是 / 值得注意的是 / 可以看出 / 由此可见 / 总体来看` are not banned. Review them when they repeat densely.

Prefer integrating the caveat directly:

- `需要说明的是，两项结果的口径不同。`
- → `两项结果采用的指标口径不同，因此不能直接进行数值比较。`

The caveat stays; the meta shell disappears.

### 4. Sentence rhythm and clause overload

Break very long sentences only at real semantic boundaries. A split must not separate a number from its condition, a claim from its citation, or a conclusion from its scope limitation.

Mix sentence lengths naturally. Do not pursue artificial “human variation” at the cost of clarity.

### 5. Empty academic filler

Review phrases such as `具有重要意义 / 提供参考 / 奠定基础 / 广阔前景` when the sentence contributes no concrete implication.

Prefer deleting empty filler or replacing it with a specific consequence. Keep it when the assignment genuinely expects a significance statement and the sentence is concrete.

### 6. Abstract and conclusion

These sections receive disproportionate reader attention and are common locations for template language or overclaiming.

Polish them for:

- concise scope;
- clear contribution/coverage;
- consistent claim strength with the body;
- no duplicated body summary;
- no generic closing sentence that adds no information.

Do not make the abstract/conclusion stronger than the evidence-reviewed body.

### 7. Student/course-level calibration

For undergraduate coursework, aim for competent technical Chinese rather than journal-editorial grandiosity. Avoid both extremes:

- overly polished institutional slogans and sweeping field-level judgments;
- fake colloquialism, fake personal experience, deliberate mistakes, or simplistic language intended to “look human”.

Naturalness should come from concrete content and purposeful organization.

## Targeted workflow

After precision/citation/requirement audits:

1. save/copy the audited draft as the **pre-polish baseline**;
2. run:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" scan --root . --input "delivery/final-audited.docx" --level auto
```

3. review only the required/high-value findings;
4. for each required finding, record `keep`, `revised`, or `not-applicable` in `references/research/prose-polish.json`, plus a **finding-specific** `revision_note`;
5. revise targeted passages only; do not regenerate the whole paper by default;
6. run the invariant guard:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" guard --root . --before "delivery/final-audited.docx" --after "delivery/final.docx"
```

7. inspect every guard warning. If a changed citation/number/technical anchor is an intentional evidence-backed correction, document it as an evidence correction rather than silently treating it as prose polish;
8. run:

```powershell
python "$HOME/.agents/skills/cnki-academic-writing-v2/scripts/prose_polish.py" audit --root . --level auto
```

9. perform a short final precision check only where wording changed materially;
10. apply `references/05-DELIVERY-QA.md`: render the final document and visually inspect the required pages before claiming layout passed.

## Audit-level behavior

- **LOW:** required polish review only for high-severity findings.
- **MEDIUM:** required review for high + medium findings. Low findings are optional.
- **HIGH:** review all generated polish findings.

This is a minimum review floor, not an edit quota. `keep` is a valid outcome.

## Stop rule

Stop polishing when the remaining edits are mainly matters of taste or would risk changing technical meaning. More rewriting is not automatically better writing.


## Review-rationale quality (V2.7)

`keep` is a real judgment, not a placeholder. The rationale must explain **why this specific finding is safe to keep** (for example: incompatible source conditions require explicit attribution; splitting would detach a parameter from its result; the abstract sequence is a conventional scope summary).

Do not paste one generic rationale across unrelated `citation-led-cadence`, `clause-overload`, filler, and meta-phrase findings. `prose_polish.py audit` now warns when the same rationale is repeated across three or more findings spanning multiple pattern types.
