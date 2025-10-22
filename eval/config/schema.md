### Config Schema

- `paths`:
  - `scenarios`: base dir for task cards by workflow.
  - `goldens`: base dir for golden labels by workflow.
  - `canary`: base dir for canary tasks.
  - `judges`: judge assets (prompts/calibration).
  - `reports`: output directory for per-run artifacts.
  - `registry`: append-only registry directory (parquet/csv files).

- `thresholds`:
  - `w1.path_match_required` (bool): if true, at least one predicted path must match a golden path exactly.
  - `w1.line_iou_min` (float 0..1): minimum IoU per matched path; use per-path averages.
  - `w1.require_symbol_match` (bool): if `inputs.symbol` exists, require mention/reference in answer.rationale.
  - `w1.faithfulness_required` (bool): if true, must have citations and quotes.
  - `canary.require_100_percent` (bool): all canary tasks must pass or the run fails.

- `judge`:
  - `enabled_for_w2` (bool): gate model-based judging for W2.
  - `model_name` (str): model id; can be blank for stub.
  - `max_tokens` (int): output cap for judge calls.
  - `temperature` (float): sampling temperature.

- `latency_cost_slo`:
  - `p95_latency_ms` (int): max allowed p95 latency.
  - `max_tokens_in` (int): total tokens in prompts per task.
  - `max_tokens_out` (int): total tokens in responses per task.
  - `max_context_tokens` (int): context window guardrail.

- `run`:
  - `seed` (int): RNG seed for sampling.
  - `fail_fast_on_canary` (bool): stop after canary failure.
  - `report_format` (list[str]): which formats to write per-task results.

- `sut_cli`:
  - `cmd` (str): shell-invoked command to run the SUT.
  - `extra_args` (list[str]): additional args appended for all runs.
  - `timeout_s` (int): per-task timeout.

### Env overrides

- `EVAL_MODEL_NAME` → `judge.model_name`
- `EVAL_P95_LATENCY_MS` → `latency_cost_slo.p95_latency_ms`
- `EVAL_SUT_CMD` → `sut_cli.cmd`
- `EVAL_TIMEOUT_S` → `sut_cli.timeout_s`
- Any path key can be overridden with `EVAL_PATH_<KEY>` (e.g., `EVAL_PATH_REPORTS`).

