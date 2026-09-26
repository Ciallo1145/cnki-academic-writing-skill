#!/usr/bin/env python3
"""Initialize and audit the V2.6 course-paper research + precision-audit workspace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2.7"
ACCEPTED_SCHEMA_VERSIONS = {"2.4", "2.5", "2.5.4", "2.5.5", "2.5.6", "2.6.0", "2.6.1", "2.6.2", "2.7"}


def ref_dir(root: Path) -> Path:
    return root / "references" / "cnki"


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists(): return default
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else default
    except (OSError,json.JSONDecodeError): return default


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def cmd_init(root: Path) -> int:
    refs=ref_dir(root); research=root/"references"/"research"; assignment=root/"assignment"
    for d in [refs,research,assignment,assignment/"source-files",assignment/"extracted",assignment/"rendered",root/"papers"/"cnki",root/"draft",root/"delivery"]:
        d.mkdir(parents=True, exist_ok=True)
    defaults={
      refs/"candidates.json":{"schema_version":SCHEMA_VERSION,"searches":[],"papers":[]},
      refs/"verified.json":{"schema_version":SCHEMA_VERSION,"papers":[]},
      refs/"fulltext-manifest.json":{"schema_version":SCHEMA_VERSION,"papers":[]},
      research/"synthesis-matrix.json":{"schema_version":SCHEMA_VERSION,"claims":[]},
      research/"precision-audit.json":{"schema_version":SCHEMA_VERSION,"source":None,"summary":{},"style_scan":{},"style_findings":[],"metric_findings":[],"claims":[]},
      research/"prose-polish.json":{"schema_version":SCHEMA_VERSION,"source":None,"summary":{},"polish_findings":[]},
      research/"prose-guard.json":{"schema_version":SCHEMA_VERSION,"status":"not_run","warnings":[],"changes":{}},
      assignment/"source-manifest.json":{"schema_version":SCHEMA_VERSION,"sources":[]},
      assignment/"template-candidates.json":{"schema_version":SCHEMA_VERSION,"candidates":[]},
      assignment/"template-spec.json":{"schema_version":SCHEMA_VERSION,"status":"not_selected","source_ref":None,"source_path":None,"delivery_strategy":None,"page_setup":{},"styles":{},"fixed_elements":[],"placeholders":[],"required_fields":[],"notes":[]},
      assignment/"requirement-conflicts.json":{"schema_version":SCHEMA_VERSION,"conflicts":[]},
      assignment/"requirement-completeness.json":{"schema_version":SCHEMA_VERSION,"status":"unassessed","fields":[],"proceed_decision":"proceed","blocking_unknowns":[],"notes":[]},
      assignment/"agent-decisions.json":{"schema_version":SCHEMA_VERSION,"decisions":[]},
      assignment/"requirements.json":{
        "schema_version":SCHEMA_VERSION,"status":"unparsed","source_notes":[],"requirement_evidence":[],
        "hard_constraints":{
          "topic":None,"word_count":{"target":None,"min":None,"max":None},"required_sections":[],
          "reference_count":{"min":None,"max":None},"source_languages":[],"source_types_required":[],
          "source_types_forbidden":[],"date_range":{"from":None,"to":None},"citation_style":None,
          "format_template":None,"required_content":[],"ai_use_rules":None,"submission_format":None
        },
        "soft_preferences":{},"defaults_adopted":[],"unresolved":[]
      }
    }
    for p,payload in defaults.items():
        if not p.exists(): write_json(p,payload)
    for p,heading in {
      refs/"search-log.md":"# CNKI Search Log\n",refs/"bibliography.md":"# Bibliography\n",refs/"citation-audit.md":"# Citation Audit\n",refs/"precision-audit.md":"# Precision Audit Queue\n",refs/"prose-polish.md":"# Evidence-Safe Prose Polish Queue\n",assignment/"requirements.md":"# Course / Assignment Requirements\n"
    }.items():
        if not p.exists(): p.write_text(heading, encoding="utf-8")
    print(str(root.resolve())); return 0


def cmd_audit(root: Path) -> int:
    refs=ref_dir(root); assignment=root/"assignment"
    verified_path=refs/"verified.json"; fulltext_path=refs/"fulltext-manifest.json"
    requirements_path=assignment/"requirements.json"; completeness_path=assignment/"requirement-completeness.json"; synthesis_path=root/"references"/"research"/"synthesis-matrix.json"; precision_path=root/"references"/"research"/"precision-audit.json"
    source_manifest_path=assignment/"source-manifest.json"; template_spec_path=assignment/"template-spec.json"; conflicts_path=assignment/"requirement-conflicts.json"; decisions_path=assignment/"agent-decisions.json"
    warnings=[]
    verified=load_json(verified_path,{"papers":[]}); fulltext=load_json(fulltext_path,{"papers":[]}); requirements=load_json(requirements_path,{}); completeness=load_json(completeness_path,{})
    synthesis=load_json(synthesis_path,{"claims":[]}); precision=load_json(precision_path,{"claims":[]}); sources=load_json(source_manifest_path,{"sources":[]}); template=load_json(template_spec_path,{})
    conflicts=load_json(conflicts_path,{"conflicts":[]}); decisions=load_json(decisions_path,{"decisions":[]})

    if not requirements_path.exists(): warnings.append("assignment/requirements.json is missing")
    else:
        if requirements.get("schema_version") not in (*ACCEPTED_SCHEMA_VERSIONS,None): warnings.append("assignment/requirements.json: unexpected schema_version")
        if requirements.get("status")=="unparsed": warnings.append("assignment requirements are still unparsed")
        for key in ("hard_constraints","defaults_adopted","unresolved"):
            if key not in requirements: warnings.append(f"assignment/requirements.json: missing {key}")

    if not completeness_path.exists():
        warnings.append("assignment/requirement-completeness.json is missing")
    else:
        if completeness.get("schema_version") not in (*ACCEPTED_SCHEMA_VERSIONS,None): warnings.append("assignment/requirement-completeness.json: unexpected schema_version")
        if completeness.get("status") in (None,"unassessed"): warnings.append("assignment requirement completeness is still unassessed")
        fields=completeness.get("fields",[])
        if not isinstance(fields,list):
            warnings.append("requirement-completeness.json: fields must be a list")
            fields=[]
        valid_req_states={"confirmed","defaulted","blocking_unknown","not_applicable"}
        for idx,item in enumerate(fields,1):
            if not isinstance(item,dict):
                warnings.append(f"requirement-completeness field #{idx}: must be an object"); continue
            state=item.get("status")
            if state not in valid_req_states:
                warnings.append(f"requirement-completeness field #{idx}: invalid status {state!r}")
            if state=="defaulted" and item.get("source") not in ("skill_default","user_default"):
                warnings.append(f"requirement-completeness field #{idx}: defaulted item should identify skill_default/user_default source")
            if state=="blocking_unknown" and item.get("resolved") is not True:
                warnings.append(f"requirement-completeness field #{idx}: unresolved blocking_unknown: {item.get('field') or '<field>'}")
        blockers=completeness.get("blocking_unknowns",[])
        if not isinstance(blockers,list):
            warnings.append("requirement-completeness.json: blocking_unknowns must be a list"); blockers=[]
        for idx,item in enumerate(blockers,1):
            if isinstance(item,dict) and item.get("resolved") is True:
                continue
            warnings.append(f"requirement-completeness blocking_unknown #{idx} is unresolved")
        if completeness.get("proceed_decision")=="needs_user_input" and blockers:
            warnings.append("requirement completeness requires user input before final delivery")


    # Material deviations from non-binding defaults are optional, but if recorded they must be explainable.
    if decisions_path.exists():
        if decisions.get("schema_version") not in (*ACCEPTED_SCHEMA_VERSIONS,None): warnings.append("assignment/agent-decisions.json: unexpected schema_version")
        decision_rows=decisions.get("decisions",[])
        if not isinstance(decision_rows,list):
            warnings.append("agent-decisions.json: decisions must be a list"); decision_rows=[]
        for idx,item in enumerate(decision_rows,1):
            if not isinstance(item,dict):
                warnings.append(f"agent decision #{idx}: must be an object"); continue
            if not item.get("decision"):
                warnings.append(f"agent decision #{idx}: missing decision")
            if item.get("layer") not in (None,"default_policy","agent_discretion"):
                warnings.append(f"agent decision #{idx}: invalid layer {item.get('layer')!r}")
            # A material deviation should not be opaque. Avoid requiring verbose logs.
            if item.get("status","applied") == "applied" and not item.get("reason"):
                warnings.append(f"agent decision #{idx}: applied material deviation missing reason")

    source_rows=sources.get("sources",[])
    if not isinstance(source_rows,list): warnings.append("source-manifest.json: sources must be a list"); source_rows=[]
    valid_source_ids=set()
    for s in source_rows:
        if not isinstance(s,dict): warnings.append("source-manifest.json: non-object source record"); continue
        sid=str(s.get("source_id") or "")
        if sid: valid_source_ids.add(sid)
        stored=s.get("stored_path") or s.get("original_path")
        if stored and not Path(str(stored)).expanduser().exists(): warnings.append(f"{sid or '<source>'}: source path does not exist: {stored}")
        if s.get("needs_vision") is True and s.get("vision_review_status") != "reviewed":
            warnings.append(f"{sid or '<source>'}: visual review required but not marked reviewed")

    req_evidence=requirements.get("requirement_evidence",[]) if isinstance(requirements,dict) else []
    if isinstance(req_evidence,list):
        for idx,e in enumerate(req_evidence,1):
            if isinstance(e,dict):
                ref=str(e.get("source_ref") or "")
                if ref and ref not in valid_source_ids: warnings.append(f"requirement_evidence #{idx}: source_ref {ref} not found in source-manifest")

    if template.get("status") == "selected":
        ref=str(template.get("source_ref") or "")
        path=template.get("source_path")
        if not ref: warnings.append("template-spec: selected but source_ref missing")
        elif ref not in valid_source_ids: warnings.append(f"template-spec: source_ref {ref} not found in source-manifest")
        if not path: warnings.append("template-spec: selected but source_path missing")
        elif not Path(str(path)).expanduser().exists(): warnings.append(f"template-spec: source_path does not exist: {path}")
        if not template.get("delivery_strategy"): warnings.append("template-spec: selected but delivery_strategy missing")

    conflict_rows=conflicts.get("conflicts",[])
    if not isinstance(conflict_rows,list): warnings.append("requirement-conflicts.json: conflicts must be a list"); conflict_rows=[]
    for i,c in enumerate(conflict_rows,1):
        if isinstance(c,dict) and c.get("blocking") is True and not c.get("resolved"):
            warnings.append(f"requirement conflict #{i} is blocking and unresolved")

    vpapers=verified.get("papers",[]); fpapers=fulltext.get("papers",[]); claims=synthesis.get("claims",[])
    detailed_records=verified.get("records",[]) if isinstance(verified,dict) else []
    if not isinstance(detailed_records,list): detailed_records=[]
    if not isinstance(vpapers,list): warnings.append("verified.json: papers must be a list"); vpapers=[]
    if not isinstance(fpapers,list): warnings.append("fulltext-manifest.json: papers must be a list"); fpapers=[]
    if not isinstance(claims,list): warnings.append("synthesis-matrix.json: claims must be a list"); claims=[]
    full_by_row={}
    for p in fpapers:
        if not isinstance(p,dict): warnings.append("fulltext-manifest.json: non-object paper record"); continue
        row=str(p.get("row_id") or "")
        if row: full_by_row[row]=p
        if p.get("evidence_level")=="fulltext-verified":
            local=p.get("local_fulltext_path")
            if not local: warnings.append(f"{row or '<unknown>'}: fulltext-verified but local_fulltext_path missing")
            else:
                path=Path(str(local)).expanduser()
                if not path.exists(): warnings.append(f"{row or '<unknown>'}: fulltext path does not exist: {path}")
            for key in ("file_exists_verified","parse_verified","read_verified"):
                if p.get(key) is not True: warnings.append(f"{row or '<unknown>'}: fulltext-verified but {key} is not true")
    valid_rows=set()
    for p in vpapers:
        if not isinstance(p,dict): warnings.append("verified.json: non-object paper record"); continue
        row=str(p.get("row_id") or "")
        if row: valid_rows.add(row)
        for key in ("row_id","workspace_id","run_id","title","evidence_level"):
            if not p.get(key): warnings.append(f"{row or '<unknown>'}: verified record missing {key}")
        if p.get("evidence_level")=="fulltext-verified":
            fp=full_by_row.get(row)
            if not fp or fp.get("evidence_level")!="fulltext-verified": warnings.append(f"{row or '<unknown>'}: verified.json says fulltext-verified but manifest does not")
        doi=p.get("doi"); doi_status=p.get("doi_status")
        if doi and doi_status in (None,"not_returned","not_verified"): warnings.append(f"{row or '<unknown>'}: DOI present but doi_status is not verified")

    # V2.5.6 separates evidence level from reading scope. `fulltext-verified` means a
    # legitimate local full-text source was parsed and the relevant evidence was actually
    # read; it does not imply every page was read. Detailed records should preserve scope.
    full_read_count=0
    targeted_read_count=0
    read_scope_unknown_count=0
    final_abstract_claim_records=0
    for rec in detailed_records:
        if not isinstance(rec,dict):
            continue
        ev=rec.get("evidence_level")
        used=rec.get("used_in_final") is True or rec.get("citation_number") not in (None, "")
        intended=rec.get("intended_claims",[])
        if ev=="fulltext-verified":
            ft=rec.get("fulltext",{}) if isinstance(rec.get("fulltext",{}),dict) else {}
            scope=ft.get("read_scope") or rec.get("read_scope")
            if scope=="full":
                full_read_count += 1
            elif scope in {"targeted-sections","targeted_sections","targeted"}:
                targeted_read_count += 1
            else:
                read_scope_unknown_count += 1
                # Only enforce the new field on projects already using the 2.5.6 schema.
                if verified.get("schema_version") in {"2.5.6", SCHEMA_VERSION}:
                    warnings.append(f"{rec.get('id') or rec.get('row_id') or '<unknown>'}: fulltext-verified record missing valid read_scope (full/targeted-sections)")
        if used and ev=="abstract-verified":
            final_abstract_claim_records += 1
            if not isinstance(intended,list) or not [x for x in intended if str(x).strip()]:
                warnings.append(f"{rec.get('id') or rec.get('row_id') or '<unknown>'}: final abstract-verified source has no intended_claims")
            scope=rec.get("claim_source_scope")
            if scope not in ("abstract", "details", "abstract+details"):
                warnings.append(f"{rec.get('id') or rec.get('row_id') or '<unknown>'}: final abstract-verified source should record claim_source_scope=abstract/details/abstract+details")

    for idx,claim in enumerate(claims,1):
        if not isinstance(claim,dict): warnings.append(f"synthesis claim #{idx}: must be an object"); continue
        if not claim.get("claim_id"): warnings.append(f"synthesis claim #{idx}: missing claim_id")
        if not claim.get("claim"): warnings.append(f"synthesis claim #{idx}: missing claim")
        for bucket in ("supporting_sources","limiting_or_conflicting_sources"):
            items=claim.get(bucket,[])
            if not isinstance(items,list): warnings.append(f"{claim.get('claim_id') or '#'+str(idx)}: {bucket} must be a list"); continue
            for source in items:
                if isinstance(source,dict):
                    ref=str(source.get("source_ref") or "")
                    if ref.startswith("cnki:"):
                        row=ref.split(":",1)[1]
                        if row and row not in valid_rows: warnings.append(f"{claim.get('claim_id') or '#'+str(idx)}: source_ref {ref} not found in verified.json")

    precision_claims=precision.get("claims",[]) if isinstance(precision,dict) else []
    if not isinstance(precision_claims,list): warnings.append("precision-audit.json: claims must be a list"); precision_claims=[]
    for c in precision_claims:
        if not isinstance(c,dict): continue
        if c.get("risk_level") != "high": continue
        status=c.get("audit_status")
        verdict=c.get("verdict")
        if status in (None,"pending"):
            warnings.append(f"{c.get('claim_id') or '<precision-claim>'}: precision audit pending")
        if verdict in ("unsupported","partially-supported","context-mismatch","overstated","needs-evidence") and not c.get("revision"):
            warnings.append(f"{c.get('claim_id') or '<precision-claim>'}: {verdict} without recorded revision/removal")
        if verdict in ("supported","corrected","softened") and ("numeric-claim" in c.get("risk_tags",[]) or "strong-claim" in c.get("risk_tags",[])) and not c.get("evidence"):
            warnings.append(f"{c.get('claim_id') or '<precision-claim>'}: reviewed high-risk claim has no evidence locator")
    result={
        "status":"ok" if not warnings else "warning",
        "requirements_status":requirements.get("status") if requirements else None,
        "requirement_completeness_status":completeness.get("status") if completeness else None,
        "assignment_sources":len(source_rows),
        "verified_records":len(vpapers),
        "fulltext_records":len(fpapers),
        "fulltext_verified_count":sum(1 for p in vpapers if isinstance(p,dict) and p.get("evidence_level")=="fulltext-verified"),
        "full_read_count":full_read_count,
        "targeted_section_read_count":targeted_read_count,
        "read_scope_unknown_count":read_scope_unknown_count,
        "final_abstract_claim_records":final_abstract_claim_records,
        "synthesis_claims":len(claims),
        "precision_claims":len(precision_claims),
        "agent_decisions":len(decisions.get("decisions",[])) if isinstance(decisions,dict) and isinstance(decisions.get("decisions",[]),list) else 0,
        "warnings":warnings
    }
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if not warnings else 1


def main() -> int:
    p=argparse.ArgumentParser(description="Initialize/audit a CNKI Academic Writing V2.6 project ledger")
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("init","audit"):
        s=sub.add_parser(name); s.add_argument("--root",default=".")
    a=p.parse_args(); root=Path(a.root).expanduser().resolve()
    return cmd_init(root) if a.command=="init" else cmd_audit(root)

if __name__=="__main__": raise SystemExit(main())
