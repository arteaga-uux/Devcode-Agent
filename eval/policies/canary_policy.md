# Canary Policy

## Purpose

Canaries are non-regression gates for W1 (Definition Localization). They cover critical patterns:
- Re-export confusion (header vs source)
- Vendor/test shadow paths
- Worker vs manager distinctions
- Wayland vs XDMCP protocols
- Symbol case sensitivity

## Selection

**Target size**: 15-20 tasks, representative and stable

**Selection criteria**:
- High impact (core functionality)
- Reproducible across runs
- Unambiguous ground truth
- Low execution time (<2s per task)

**Coverage requirements**:
- All major codebase patterns
- Edge cases (case sensitivity, path confusion)
- Critical failure modes

## Gate

**PR enforcement**:
- 100% PathMatch and Faithfulness required
- Line IoU ≥ threshold (from config)
- Thresholds driven by `eval/config/config.yaml`:
  - `thresholds.canary.require_100_percent`
  - `thresholds.w1.line_iou_min`
  - `thresholds.w1.faithfulness_required`

**Failure behavior**:
- If `fail_fast_on_canary=true`: PR job fails immediately
- Clear error message with failing task IDs and reasons

## Change Control

**Immutability**: Canaries are immutable except for:
- Bug in golden (incorrect paths/ranges)
- Specification change (new requirements)

**Change process**:
1. Open PR with justification
2. Review by eval team
3. Document in change log
4. Update canary set if needed

**Change log format**:
| Date | Task ID | Reason | Reviewer |
|------|---------|--------|----------|
| 2024-01-15 | w1-c1 | Fixed incorrect line range | @reviewer |
| 2024-01-22 | w1-c5 | Updated for new spec | @reviewer |

## Promotion/Demotion

**Promotion criteria**:
- New failure is critical and stable (2+ runs)
- Adds unique coverage
- Passes all quality checks

**Demotion criteria**:
- Flaky behavior (inconsistent results)
- No longer relevant
- Replaced by better test

**Process**:
- Document cause and replacement
- Update canary set
- Re-run full validation

## Incident Response

**Gate failure on main**:
1. Freeze merges immediately
2. Open issue "Canary Triage" with:
   - Run ID
   - Failing task IDs
   - Taxonomy labels
   - Owner assignment
   - ETA for resolution
   - Link to detailed report

**Resolution steps**:
1. Investigate root cause
2. Fix SUT or update golden
3. Validate fix with full run
4. Re-enable merges
5. Document incident

## Ownership

**Current owner**: [Your name] (temporary until team assignment)

**Responsibilities**:
- Monitor canary health
- Review change requests
- Incident response
- Regular validation runs

**Handoff process**:
- Document all procedures
- Train new owner
- Transfer access and permissions
