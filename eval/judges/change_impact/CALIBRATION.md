# W2 Change-Impact Judge Calibration

## Scope

The W2 judge evaluates change-impact answers against five criteria:
- **anchors_present**: All required anchors are referenced
- **cites_relevant**: Citations correspond to the anchored files/lines  
- **no_contradictions_with_cited_lines**: Quotes support the claims
- **no_overclaim**: Answer does not claim modules outside scope/anchors
- **meets_constraints**: Honors constraints (exclude_dirs, must_cite)

The judge does not grade style, grammar, or subjective quality.

## Human Set & Protocol

**Target size**: 20-50 items with stratified sampling by tags:
- xdmcp (25%)
- wayland (25%) 
- manager_vs_worker (25%)
- other (25%)

**Annotation protocol**:
- Two annotators per item
- Adjudication for disagreements
- Fields per item: `task_id`, `human_pass` (0/1), `reasons[]`, `difficulty` (1-5)

**Sampling criteria**:
- Mix of pass/fail cases
- Representative of edge cases (forbidden claims, missing anchors)
- Include both clear and ambiguous cases

## Agreement & Acceptance Bars

**Metrics**:
- Human↔Human: Cohen's κ or % agreement
- Judge↔Human: Cohen's κ or % agreement

**Acceptance criteria**:
- κ ≥ 0.6 (or ≥0.7 for small sets)
- Judge↔Human agreement within 10pp of Human↔Human

**Procedure if below threshold**:
1. Review disagreement cases
2. Refine prompt/rubric
3. Re-annotate subset
4. Re-measure agreement

## Anchors for Drift

**Anchor set**: 5 items (not used for tuning)
- Run weekly against current judge
- If judge↔human drops >10pp: trigger re-prompt/tune
- Re-measure on full set after changes

**Anchor selection**:
- Stable, unambiguous cases
- Mix of pass/fail
- Representative of common patterns

## Separation & Pinning

**Model separation**: Judge model ≠ SUT model
- Document model/version (hash/prompt digest)
- Prohibited auto-updates without recalibration
- Version pinning in config

**Change tracking**:
- Prompt digest (hash of prompt.md)
- Model version/commit
- Calibration metrics

## Change Log

| Date | Prompt Digest | Model Version | Human κ | Judge κ | Change Reason |
|------|---------------|---------------|---------|---------|---------------|
| 2024-01-15 | abc123def | gpt-4o-mini-2024-01-15 | 0.72 | 0.68 | Initial calibration |
| 2024-01-22 | def456ghi | gpt-4o-mini-2024-01-15 | 0.72 | 0.71 | Prompt refinement |
| TODO | TODO | TODO | TODO | TODO | Replace with real data |

## Quality Gates

**Promotion criteria** (to `enabled_for_w2=true`):
- κ ≥ 0.6 (or ≥0.7 for small sets)
- All anchors green (no drift)
- No degradation in W1 canaries
- Stable performance over 3+ runs

**Monitoring**:
- Weekly anchor runs
- Monthly full calibration check
- Quarterly human re-annotation subset

**Rollback procedure**:
- If drift detected: disable judge, investigate
- Re-calibrate before re-enabling
- Document incident and resolution
