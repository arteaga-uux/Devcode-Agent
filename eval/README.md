### Evaluation Harness

This directory contains a production-lean evaluation harness for a coding assistant (SUT) that answers questions about a C/DBus codebase (GNOME GDM daemon–style).

- All assets live under `eval/`. The SUT code remains in `src/` and is queried via `api/query_agent.py`.
- Two workflows:
  - W1 Definition Localization (deterministic) — implemented end-to-end.
  - W2 Change-Impact (hybrid deterministic + judge-lite) — runnable skeleton with judge stubbed.
- Centralized configuration in `eval/config/config.yaml`, loaded by a typed loader in `eval/runner/config.py`.
- Logs quality × latency × cost, canary gate enforcement, append-only run registry, and minimal token spend.

### Layout

- `config/`: centralized configuration (`config.yaml`), schema notes, optional env overrides.
- `scenarios/`: task cards grouped by workflow.
- `goldens/`: ground truth labels.
- `canary/`: small passing subset for gating.
- `metrics/`: deterministic metrics.
- `runner/`: runners, config loader, and utilities.
- `judges/`: judge prompts and calibration examples (W2 stub).
- `registry/`: append-only registry of runs and manifest.
- `reports/`: per-run artifacts.

### Quickstart

1) Ensure a SUT CLI exists at `api/query_agent.py` exposing `python -m api.query_agent --task_file <file.json>`.
   - If missing, a mock SUT is scaffolded and will echo structured responses.

2) Configure `eval/config/config.yaml`. You can override keys via environment variables (see `.env.example`).

3) Run W1 (localization):

```bash
python -m eval.runner.run_localization --suite all
```

This will run the canary gate first, then the full W1 suite, compute metrics/taxonomy, and write `reports/<run_id>/`.

### CI & Canary Gate

- Canaries live at `eval/canary/w1_localization/` with corresponding goldens in `eval/goldens/w1_localization/`.
- Policy: canaries must be 100% green on PRs. The gate respects config:
  - `thresholds.canary.require_100_percent`
  - `thresholds.w1.line_iou_min`
  - `run.fail_fast_on_canary`
- Local check:

```bash
python -m eval.runner.run_localization --suite canary
```

- Nightly job runs `--suite all` and uploads `eval/reports/<run_id>`; results are appended to `eval/registry/runs.parquet`.
- Override behavior by editing `eval/config/config.yaml` (ENV > YAML > defaults).

### Config knobs

See `config/schema.md`. Tune thresholds, SUT command, timeouts, judge toggles, and SLOs in `config.yaml`.

### Adding tasks and goldens

- Task card schema (YAML/JSON):
  - `id`, `workflow` ("w1_localization"|"w2_change_impact"),
  - `inputs` { `symbol?`, `callsite?` },
  - `constraints` { `must_cite`, `exclude_dirs[]` },
  - `acceptance_criteria` { `paths[]`, `line_ranges[[s,e]]`, `checklist[]` },
  - `tags[]`.
- Golden schema (JSONL):
  - `task_id`, `paths[]`, `line_ranges[[s,e]]`, `quotes[]`, `provenance` { `repo`, `commit` }, `notes`.

### Flywheel

- Promote hard failures from reports into canaries in `canary/w1_localization/`.
- Keep canaries fast and passing. Fail fast on PRs.

### CI

- See `.github/workflows/evals.yml`.
- PRs: run canaries only.
- Nightly: full W1 + small W2. Upload `reports/<run_id>` as artifact.

### W2 Change-Impact

- Success = all required anchors are cited and faithful to example quotes, no forbidden claims, and (optionally) judge-lite passes if enabled.
- Failure labels: `anchors_missing`, `anchors_unfaithful`, `forbidden_claim`, plus SLO breaches.

Authoring W2 goldens:
- Put tasks in `scenarios/w2_change_impact/` with `acceptance_criteria.required_anchors` (path/kind/symbol?), optional `forbidden_claims`, and `checklist`.
- Put goldens in `goldens/w2_change_impact/goldens.jsonl` with `required_anchors` + `example_quotes` (path/start/end/quote).

Judge-Lite:
- Disabled by default; deterministic core provides most signal.
- When enabled via config, a stub simulates pass only when deterministic core passes; a future LLM call will be plugged using `judges/change_impact/prompt.md` and calibration examples.

### Before/After & Trends

Compare runs:
```bash
python -m eval.runner.diff_runs --before <run_id_A> --after <run_id_B>
```

Show trends over last N runs:
```bash
python -m eval.runner.diff_runs --before <run_id_A> --after <run_id_B> --last 5
```

The tool prints a compact table with W1/W2 metrics, deltas (▲/▼), and a conclusion line. Cross-validates registry vs reports/summary.json and warns on mismatches.

### Adversarial Variants (deterministic)

Generate controlled near-duplicate tasks to stress robustness without LLM tokens:

```bash
python -m eval.utils.variants --source eval/goldens/w1_localization --out eval/scenarios/w1_localization --limit 10
```

Variant kinds:
- `case`: Toggle symbol case (normalizeUrl ↔ normalizeURL)
- `reexport`: Add synthetic re-export layer (daemon/foo.c → daemon/index.c)
- `test`: Create test shadow (daemon/foo.c → tests/daemon/foo.c)
- `vendor`: Create vendor shadow (daemon/foo.c → vendor/daemon/foo.c)
- `nearname`: Minimal edit distance (gdm_display_factory_create_display → gdm_display_factory_create_displays)

Run with variants:
```bash
python -m eval.runner.run_localization --include-variants
```

Truth unchanged: variants reference original goldens; scoring remains deterministic. Variants are not canaries unless manually promoted.

## Eval Flywheel

Continuous improvement loop: run → tag failures (taxonomy) → curate useful cases → promote to goldens → adjust thresholds → re-run.

**Promotion checklist**:
- [ ] Failure is reproducible across runs
- [ ] Not a near-duplicate of existing golden
- [ ] Adds new coverage (path/pattern not covered)
- [ ] Golden includes complete paths, line_ranges, quotes
- [ ] Provenance.repo/commit is complete and valid

**Review process**: Changes to goldens require PR and review. Anchor items (judge drift) are never tuned.

## Reproducibility & SLOs

| Dimension | Key | Default | Config Path |
|-----------|-----|---------|-------------|
| Line IoU min | thresholds.w1.line_iou_min | 0.6 | eval/config/config.yaml |
| Faithfulness required | thresholds.w1.faithfulness_required | true | eval/config/config.yaml |
| p95 Latency (ms) | latency_cost_slo.p95_latency_ms | 5000 | eval/config/config.yaml |
| Max tokens in | latency_cost_slo.max_tokens_in | 20000 | eval/config/config.yaml |
| Max tokens out | latency_cost_slo.max_tokens_out | 4000 | eval/config/config.yaml |
| Max context tokens | latency_cost_slo.max_context_tokens | 50000 | eval/config/config.yaml |

All runners read knobs from config; `--dry-run` prints effective config.

## Run Registry & Diffs

**Reports**: `eval/reports/<run_id>/` (summary.json, *_by_task.csv)
**Registry**: `eval/registry/runs.parquet` (append-only)
**Diffs**: `python -m eval.runner.diff_runs --before <A> --after <B>`

Interpret ▲/▼ as improvement/degradation; validate canary_ok status.

