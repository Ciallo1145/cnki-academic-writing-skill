# CNKI Academic Writing V2.7.3 — Audit


## Audit levels

## Purpose

The three audit levels change **depth**, not academic honesty. LOW never means “skip verification”, and HIGH never means “blindly reread every paper”. Each level defines a **minimum coverage floor**, not a ceiling: capable agents may add targeted checks when useful, but may not skip required checks or self-downgrade the resolved level.

Project setting:

```json
{
  "schema_version": 1,
  "audit_level": "medium"
}
```

Path: `assignment/workflow-config.json`

Valid values: `low`, `medium`, `high`. Missing/invalid configuration defaults to `medium`.

Priority:

1. explicit per-run user instruction (`low`, `medium`, `high`);
2. `assignment/workflow-config.json`;
3. default `medium`.

Teacher/course hard requirements, evidence-integrity rules, access-control boundaries, and safety rules are mandatory in every level and cannot be weakened by LOW.

## Mandatory baseline for every level

Always verify:

- every bibliography entry used in the paper maps to a retrieved/verified source;
- every numbered bibliography entry is actually cited in the body unless the assignment explicitly requires a separate background bibliography;
- every in-text citation resolves to the intended source;
- exact numerical/paper-specific claims have direct evidence at the level required by the Skill;
- `fulltext-verified` really has local file + parse + read verification;
- the actual full-text reading scope is recorded as `full` or `targeted-sections` rather than inferred from `fulltext-verified`;
- hard assignment/template requirements;
- obvious strong/absolute claims flagged as high risk;
- unresolved fabricated, mismatched, or inaccessible evidence is not hidden;
- key equations that drive numerical results, simulation, or conclusions are checked for both syntax/structure and independent theoretical validity; complex/high-risk key equations receive two structurally independent validation paths.

The static scanner excludes the final **reference list/bibliography** from prose claim scanning. Bibliographic correctness is handled by citation/provenance audit, not by treating reference entries as academic claims.

## LOW — fast factual safety

Goal: catch errors likely to materially harm correctness while minimizing audit cost.

Review:

- all `high` risk items;
- all exact numerical claims even if their static risk class is only `medium`;
- citation/provenance baseline;
- hard assignment/template requirements;
- citation bundles only when they are part of a high-risk/numeric claim;
- strongest abstract/conclusion statements;
- high-severity evidence-sufficiency/generalization hits;
- static structural-style scan only for high-severity repetition patterns.

Evidence checks should be highly targeted. Do not proactively triangulate ordinary claims.

## MEDIUM — default balanced audit

Goal: normal high-quality course-paper verification without turning MEDIUM into near-HIGH.

Review everything in LOW, plus **material** medium-risk claims. `risk_level == medium` does **not** automatically mean “must review”. MEDIUM prioritizes medium candidates that materially affect correctness or argument quality, including:

- strong/generalized claims;
- evidence-sufficiency review targets (`业内共识`, `首要`, `公认`, etc. when weakly sourced/unattributed);
- cross-source quantitative metric checks;
- important citation bundles;
- summary/conclusion claims with causal/comparative force;
- comparative/causal claims lacking an inline citation;
- core abstract ↔ body ↔ conclusion consistency;
- major evidence-bearing tables/figures ↔ prose ↔ source consistency;
- core synthesis-matrix coverage;
- structural AI-pattern review of all high/medium `style_findings` in flagged sections.

Ordinary medium-risk sentences that do not meet the materiality rules remain available for optional sampling but are **not mandatory**. This is the main V2.5.6 audit-noise reduction.

After targeted corrections, rerun one static scan and recheck modified/high-risk locations rather than regenerating or rereading the entire paper.

## HIGH — deep evidence audit

Goal: deeper thesis/important-paper assurance without brute-force corpus rereading.

Review everything in MEDIUM, plus:

- all high and medium claim candidates;
- low-risk technical candidates that are not merely style-only hits, especially comparative, causal, summary, and citation-cluster statements;
- nontrivial citation bundles source-by-source;
- systematic abstract/body/conclusion/table/figure/synthesis consistency;
- independent/limiting evidence for decisive conclusions where triangulation materially improves confidence;
- a second targeted verification pass after corrections;
- all structural `style_findings`, including low-severity symmetry signals, reviewed in context.

HIGH still obeys Adaptive Evidence Budget. It expands reading only for named evidence gaps; it must not reread the full corpus merely because the level is HIGH.

## Evidence sufficiency vs citation fidelity

Every level distinguishes:

- **citation fidelity**: the source truly supports the proposition;
- **evidence sufficiency**: the source set is broad/strong enough for the wording used.

A single paper may faithfully say “逐渐成为业内共识”, but that does not automatically justify presenting the phrase as an unattributed field-wide fact. Depending on importance, attribute it to the source, soften it, or triangulate with independent evidence.

## Static scanner mapping

`precise_audit.py` supports:

```powershell
python scripts/precise_audit.py audit --root . --level auto
```

`auto` reads `assignment/workflow-config.json` and defaults to `medium`.

The scanner's level is a queue/coverage rule, not a truth judgment. The model must still inspect exact evidence for flagged claims.

## Mandatory audit-gate execution

When the bundled scripts are runnable, the precision gate is not optional:

1. run `precise_audit.py scan` on the document actually being audited;
2. resolve the required queue for the effective audit level;
3. run `precise_audit.py audit` and require `status: ok` before calling the precision gate passed.

A manual review may add findings, but it does **not** replace these commands. “No existing ledger/project record” is not a valid reason to skip the scan because `scan` creates the precision-audit record itself. For an audit-only task, create only the minimal directories/files the command needs; do not invent research provenance that does not exist.

If the command is technically unavailable or fails, record the exact command and failure, continue with the best available manual review, and label the automated gate `unavailable/failed` rather than `passed`.


## Precision audit

The goal is to spend model attention on claims most likely to be wrong, overstated, mismatched to citations, internally inconsistent, or supported by evidence that is too narrow for the wording.

## What the static scanner does

`precise_audit.py scan` creates focused review queues. It does not judge truth or AI authorship.

It prioritizes:

- exact numbers and paper-specific metrics;
- strong/absolute wording such as “显著优于 / 最高 / 最优 / 完全 / 免去 / 共识”;
- causal wording;
- comparisons and superlatives;
- large citation bundles attached to one proposition;
- strong claims in abstract and conclusion;
- **evidence-sufficiency generalizations** such as `业内共识`, `公认`, `首要`, `最核心`, `必经之路` when they rely on one source or lack explicit attribution;
- **cross-source metric juxtapositions** where one paragraph combines multiple numeric values/sources around the same metric family;
- template-like or over-symmetrical writing patterns;
- section-level structural patterns such as ordered prose enumeration, repeated paragraph-opening shells, connector-start density, and unusually uniform paragraph lengths;
- numbered equations referenced by the prose, plus obvious formula-syntax defects such as unbalanced delimiters;
- numbered bibliography entries that are never cited in the body.

The final reference list is excluded from prose claim scanning. Reference entries are audited through provenance/citation checks instead. The scanner may still report a lightweight **unused-reference** finding when a numbered bibliography entry has no in-text citation.

## Claim review schema

For each claim selected by the effective audit level, fill at least:

```json
{
  "claim_id": "claim-0001",
  "audit_status": "reviewed",
  "verdict": "supported | partially-supported | context-mismatch | overstated | unsupported | needs-evidence | corrected | softened",
  "evidence": [
    {
      "source_ref": "cnki:row-0012",
      "local_path": "papers/cnki/xxx.pdf",
      "locator": "p.7, Table 3 / section 4.2 / verified abstract",
      "support_note": "exact value and condition are stated here"
    }
  ],
  "sufficiency_status": "reviewed",
  "sufficiency_verdict": "sufficient | attribute-to-source | triangulate | soften | not-applicable",
  "metric_consistency_status": "reviewed",
  "metric_consistency_verdict": "consistent | different-definition-disclosed | revised | not-applicable",
  "revision": "revised sentence or null",
  "notes": "why the wording is acceptable or changed"
}
```

Only fill sufficiency/metric fields when the corresponding static tags are present.

## MEDIUM materiality rule

V2.5.6 intentionally stops treating every static `medium` candidate as mandatory in MEDIUM mode. MEDIUM must review high-risk and numeric claims plus **material medium-risk** items, such as strong/generalized claims, important citation clusters, cross-source metric checks, summary causal/comparative claims, and uncited causal/comparative claims. Other medium candidates may be sampled but are not a mandatory queue.

HIGH still reviews all high/medium candidates.

## Strong-claim rule

A stronger word needs stronger evidence. When the underlying studies differ in dataset, SNR, channel, population, training protocol, orbit, bandwidth, or metric, prefer bounded wording:

- `在该数据集/条件下更高` instead of `最高`;
- `在部分条件下表现较好` instead of `显著优于现有方案`;
- `减少人工特征设计依赖` instead of `免去人工特征设计`.

Do not turn a paper author's cautious or rhetorical claim into a universal conclusion.

## Formula correctness — consistency is not truth

For a **key equation** that drives a numerical result, simulation, table/figure, or conclusion, do not stop at “formula ↔ code ↔ CSV ↔ prose are consistent”. That only proves the implementation follows the same formula.

Required check for material formulas:

1. inspect the rendered formula for balanced delimiters, complete function arguments, signs, subscripts/superscripts, and variable/normalization consistency;
2. independently validate the mathematics by re-derivation or authoritative cross-check;
3. when practical, test a limiting/special case or dimensional/normalization sanity condition;
4. if the formula is corrected, regenerate dependent code/results/figures/tables rather than patching only the prose.

### Complex/high-risk formula rule — two independent paths

A single self-derivation is insufficient when the formula is structurally easy to get consistently wrong. Treat a key formula as complex/high-risk when it includes, for example:

- multiple decision thresholds / piecewise regions / event partitions;
- several probability-tail terms whose coefficients depend on mapping or region counting;
- probability integrals/sums or nontrivial approximations;
- omitted-event assumptions that could change coefficients or signs;
- a derivation that directly drives simulation/plots/conclusions and is not a simple identity.

For such a formula, record **two structurally independent validation paths** in `verification_paths`. Examples of distinct methods:

- `independent-derivation`;
- `authoritative-source`;
- `decision-region-enumeration`;
- `numerical-integration`;
- `limiting-special-case`.

Example record:

```json
{
  "verification_paths": [
    {"method": "independent-derivation", "note": "derive from stated assumptions without copying the paper's algebra"},
    {"method": "decision-region-enumeration", "note": "enumerate every decision region/event and recompute bit-error contributions"}
  ]
}
```

Two repetitions of the same algebraic derivation do not count as two paths. Code/CSV/figure agreement is not an independent theoretical path when they are generated from the same equation.

The static scanner automatically marks some obvious patterns (for example multiple probability-tail terms) as `dual_validation_required`, but the model must also escalate a formula when its semantics are complex even if the scanner does not recognize the pattern.

For MEDIUM, require formula review for numbered formulas referenced later in the paper or otherwise materially driving the result; apply the two-path rule when they are complex/high-risk. HIGH may review all nontrivial numbered formulas. A simple identity that has no bearing on the conclusion need not trigger a literature search.

The static scanner can catch some **syntax** failures and can queue material numbered formulas, but it cannot determine mathematical truth. The model must perform the validity checks.

## Statistical-method naming

When the paper reports a confidence interval, p-value, hypothesis test, estimator, or similar statistic for which multiple standard methods could produce materially different numbers, name the method used (for example, Wilson vs exact binomial interval) or make the calculation method otherwise reproducible. Do not leave a method-specific number looking method-free.

## Strong attribution citation-site check

A source can be real, relevant, and correctly formatted while still being the wrong citation for a specific sentence. Treat the following high-yield attribution patterns as mandatory citation-fidelity checks:

- `文献[n]指出/表明/证明/发现/建议……`;
- `已有研究……[n]`;
- `研究表明……[n]`;
- `据文献[n]……` / `根据文献[n]……`.

For each such finding, verify the **exact proposition at that citation site** against the cited source. Do not close the finding merely because the bibliography metadata is genuine or the paper is broadly on-topic. Record a concrete locator/support note when the source supports it; otherwise correct the citation, split/soften the claim, or remove the attribution.

This is intentionally narrow: ordinary citation-bearing sentences without explicit attribution are not all promoted to mandatory review solely by this rule.

## Citation fidelity vs evidence sufficiency

These are separate questions:

1. **Citation fidelity:** did the source actually state/support the claim?
2. **Evidence sufficiency:** is one source (or the current evidence set) enough to justify the breadth/strength of the wording?

For a single-source field-wide judgment such as `业内共识` or `首要应用`, prefer one of four actions:

- attribute: `文献[12]认为……`;
- soften: `重要研究方向之一`;
- triangulate with independent evidence when the stronger wording matters;
- keep only when the evidence breadth genuinely supports it.

Do not retrieve extra literature just to preserve decorative strong wording when attribution/softening is sufficient.

## Cross-source metric consistency

When multiple sources/values appear in one paragraph/table, compare definitions before comparing values. Check at least:

- one-way vs RTT / end-to-end vs access latency;
- average vs peak vs percentile;
- per-user vs system aggregate;
- simulation vs measurement;
- different datasets/populations/channel/SNR/bandwidth/orbit assumptions;
- different denominators or evaluation protocols.

If definitions differ, disclose them, separate the values, or remove the apparent comparison. Correct citations alone do not make incompatible metrics comparable.

## Citation-bundle rule

For `[3,7-9]`, verify whether all cited sources support the complete sentence. If sources support different parts, split the sentence and attach citations to the appropriate propositions.

## Cross-section consistency

Compare abstract/body/conclusion and tables/figures/body. A caveat in the body must not disappear in the abstract or conclusion.

## Evidence-gap mode

When a claim is unsupported, do not reread the entire corpus by default. Inspect the smallest relevant page/section first. Search/download extra literature only when the claim is important and cannot be safely attributed, softened, or removed.

## Structural AI-pattern scan

The scanner writes `style_findings` with section, pattern type, severity, paragraph locations, snippets, metrics, and review state. It detects structural families instead of maintaining an endless phrase blacklist.

For each finding required by the current audit level, record `review_status: reviewed` and `resolution: keep | revised | not-applicable`. Preserve legitimate taxonomies; revise only mechanical repetition. See `STRUCTURAL-AI-PATTERNS.md`.

Phrase/structure hits are prompts for naturalness review, not AI detection. Preserve legitimate academic terminology and technical clarity.

## V2.7 evidence detail rule — only for important claims

Do not turn the audit into an evidence database. For claims that are **high-risk** or **material medium-risk**, a positive verdict (`supported`, `corrected`, or `softened`) should have at least one evidence record that:

- points to a concrete page/section/paragraph/table/figure or similarly precise local excerpt; and
- briefly states what that passage supports.

`verified full text` / `全文已核验` alone is too broad for these important claims. Ordinary low-value findings do not need this extra bookkeeping, and the rule must not be used as a reason to reread the entire literature set.

## V2.7 scan-target vs execution-summary semantics

Static scanning and completed review history are different measurements. A corrected sentence may no longer trigger the static detector, while the ledger should still remember that an issue was found and resolved.

Therefore V2.7 uses:

- `summary.evidence_sufficiency_scan_targets`: targets present in the **current scanned wording**;
- `audit_execution_summary.evidence_sufficiency_records_reviewed`: reviewed sufficiency records retained in the ledger;
- `audit_execution_summary.evidence_sufficiency_findings`: reviewed records whose disposition required action (`attribute-to-source`, `triangulate`, or `soften`);
- `audit_execution_summary.evidence_sufficiency_dispositions`: disposition counts.

Do not compare a post-correction static target count directly with historical findings and call that a contradiction. The audit command persists `audit_execution_summary` into the JSON so later reports can distinguish the two.
