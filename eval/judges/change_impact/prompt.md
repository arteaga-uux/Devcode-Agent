### Change-Impact Judge (Stub)

Checklist rubric (all must pass):
- anchors_present: All required anchors are referenced.
- cites_relevant: Citations correspond to the anchored files/lines.
- no_contradictions_with_cited_lines: Quotes support the claims.
- no_overclaim: The answer does not claim modules outside scope/anchors.
- meets_constraints: Honors `constraints` (e.g., exclude_dirs, must_cite).

Strict JSON response schema:
```json
{
  "pass": true,
  "reasons": ["anchors_present","cites_relevant"],
  "checks": {
    "anchors_present": 1,
    "cites_relevant": 1,
    "no_contradictions_with_cited_lines": 1,
    "no_overclaim": 1,
    "meets_constraints": 1
  }
}
```

Notes:
- Do not pass unless all checklist items are satisfied.
- This file is used by a future LLM judge; currently the runner uses a deterministic stub.
- Calibration examples in `calibration.jsonl` should encode human judgments for ~20 tasks.

