import os
import argparse
import sys
from statistics import median
from typing import Dict, Any, List

from .config import get_config
from .common import load_tasks_for_workflow, load_goldens_jsonl, call_sut, write_reports, append_registry, new_run_id, dry_run_info
from ..metrics.localization import evaluate_localization
from ..metrics.faithfulness import evaluate_faithfulness
from ..metrics.taxonomy import map_labels


def _evaluate_task(task: Dict[str, Any], prediction: Dict[str, Any], golden: Dict[str, Any], cfg) -> Dict[str, Any]:
	ans = prediction.get("answer", {}) or {}
	loc = evaluate_localization(ans, golden, task.get("inputs", {}))
	faith = evaluate_faithfulness(ans, prediction.get("citations", []))
	labels = map_labels(
		prediction,
		golden,
		loc,
		faith,
		{
			"line_iou_min": cfg.thresholds.w1.line_iou_min,
			"p95_latency_ms": cfg.latency_cost_slo.p95_latency_ms,
			"max_tokens_in": cfg.latency_cost_slo.max_tokens_in,
			"max_tokens_out": cfg.latency_cost_slo.max_tokens_out,
			"max_context_tokens": cfg.latency_cost_slo.max_context_tokens,
		},
	)
	passed = 1
	if cfg.thresholds.w1.path_match_required and loc["path_match"] != 1:
		passed = 0
	if loc["line_iou_min"] < cfg.thresholds.w1.line_iou_min:
		passed = 0
	if cfg.thresholds.w1.require_symbol_match and loc["symbol_match"] != 1:
		passed = 0
	if cfg.thresholds.w1.faithfulness_required and faith["faithful"] != 1:
		passed = 0
	return {
		"passed": passed,
		"loc": loc,
		"faith": faith,
		"labels": labels,
	}


def _run_suite(tasks_dir, goldens_dir, cfg) -> List[Dict[str, Any]]:
	# Handle both single dir and list of dirs
	if isinstance(tasks_dir, str):
		tasks_dirs = [tasks_dir]
	else:
		tasks_dirs = tasks_dir
	if isinstance(goldens_dir, str):
		goldens_dirs = [goldens_dir]
	else:
		goldens_dirs = goldens_dir
	
	tasks = []
	for td in tasks_dirs:
		tasks.extend(load_tasks_for_workflow(td))
	
	goldens = {}
	for gd in goldens_dirs:
		goldens.update(load_goldens_jsonl(gd))
	rows: List[Dict[str, Any]] = []
	for task in tasks:
		tid = task.get("id")
		gold = goldens.get(tid, {})
		pred = call_sut(task, cfg.sut_cli.timeout_s, cfg.sut_cli.cmd, cfg.sut_cli.extra_args)
		evald = _evaluate_task(task, pred, gold, cfg)
		row = {
			"task_id": tid,
			"path_match": evald["loc"]["path_match"],
			"line_iou_avg": evald["loc"]["line_iou_avg"],
			"line_iou_min": evald["loc"]["line_iou_min"],
			"symbol_match": evald["loc"]["symbol_match"],
			"symbol_presence_rate": evald["loc"]["symbol_presence_rate"],
			"faithful": evald["faith"]["faithful"],
			"faithfulness_reason": evald["faith"]["faithfulness_reason"],
			"label_primary": evald["labels"]["primary"],
			"label_secondary": ",".join(evald["labels"].get("secondary", [])),
			"latency_ms": (pred.get("timing", {}) or {}).get("latency_ms", 0),
			"tokens_in": (pred.get("tokens", {}) or {}).get("in", 0),
			"tokens_out": (pred.get("tokens", {}) or {}).get("out", 0),
			"context_tokens": (pred.get("tokens", {}) or {}).get("context", 0),
			"passed": evald["passed"],
		}
		rows.append(row)
	return rows


def _print_cli_summary(rows: List[Dict[str, Any]]) -> None:
	if not rows:
		print("No tasks.")
		return
	accuracy = sum(1 for r in rows if r.get("path_match") == 1 and r.get("faithful") == 1) / max(len(rows), 1)
	avg_iou = sum(r.get("line_iou_avg", 0.0) for r in rows) / max(len(rows), 1)
	latencies = [r.get("latency_ms", 0) for r in rows]
	p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
	avg_tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in rows) / max(len(rows), 1)
	print("\nW1 Summary")
	print(f"- Accuracy: {accuracy:.2f}  | Faithfulness Rate: {sum(1 for r in rows if r.get('faithful')==1)/max(len(rows),1):.2f}  | Avg IoU: {avg_iou:.2f}  | p95 Latency: {p95} ms  | Avg Tokens: {avg_tokens:.1f}")
	from collections import Counter
	ctr = Counter(r.get("label_primary") for r in rows if r.get("passed") == 0)
	top = ctr.most_common(3)
	if top:
		print("Top failure labels:")
		for k, v in top:
			print(f"- {k}: {v}")


def assert_canary_gate(cfg) -> int:
	print("Running W1 canary gate...")
	rows = _run_suite(os.path.join(cfg.paths.canary, "w1_localization"), os.path.join(cfg.paths.goldens, "w1_localization"), cfg)
	print(f"Canaries: {len(rows)} | thresholds.w1.line_iou_min={cfg.thresholds.w1.line_iou_min}")
	failures: List[str] = []
	for r in rows:
		checks = []
		if cfg.thresholds.w1.path_match_required and r.get("path_match") != 1:
			checks.append("path_match")
		if r.get("line_iou_min", 0.0) < cfg.thresholds.w1.line_iou_min:
			checks.append("line_iou_min")
		if cfg.thresholds.w1.require_symbol_match and r.get("symbol_match") != 1:
			checks.append("symbol_match")
		if cfg.thresholds.w1.faithfulness_required and r.get("faithful") != 1:
			checks.append("faithful")
		if checks:
			failures.append(f"{r.get('task_id')}: fail({','.join(checks)})")
	if cfg.thresholds.canary.require_100_percent and failures:
		print("Canary gate FAILED:")
		for f in failures:
			print(f"- {f}")
		return 1
	print("Canary gate PASSED")
	return 0


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--dry-run", action="store_true", help="Print effective config and task counts; exit")
	ap.add_argument("--suite", choices=["canary","w1","w2","all"], default="all")
	ap.add_argument("--include-variants", action="store_true", help="Include variant tasks in evaluation")
	args = ap.parse_args()
	cfg = get_config()
	if args.dry_run:
		info = dry_run_info()
		print("Effective eval config:\n")
		import json as _json
		print(_json.dumps(info["config"], indent=2))
		print("\nTask counts:")
		print(_json.dumps({k: v for k, v in info.items() if k != "config"}, indent=2))
		return
	# Canary only mode
	if args.suite == "canary":
		exit_code = assert_canary_gate(cfg)
		sys.exit(exit_code)
	# Always run canary gate before full W1
	gate_code = assert_canary_gate(cfg)
	if gate_code != 0 and cfg.run.fail_fast_on_canary:
		sys.exit(gate_code)
	# Full W1
	run_id = new_run_id()
	scenarios_dir = os.path.join(cfg.paths.scenarios, "w1_localization")
	goldens_dir = os.path.join(cfg.paths.goldens, "w1_localization")
	
	# Include variants if requested and enabled
	if args.include_variants and cfg.variants.enabled:
		scenarios_dir = [scenarios_dir, os.path.join(scenarios_dir, "variants")]
		goldens_dir = [goldens_dir, os.path.join(goldens_dir, "variants")]
	
	rows = _run_suite(scenarios_dir, goldens_dir, cfg)
	latencies = [r["latency_ms"] for r in rows if isinstance(r.get("latency_ms"), (int, float))]
	p50 = median(latencies) if latencies else 0
	p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
	avg_tokens_in = sum(r.get("tokens_in", 0) for r in rows) / max(len(rows), 1)
	avg_tokens_out = sum(r.get("tokens_out", 0) for r in rows) / max(len(rows), 1)
	# Calculate per-variant-kind metrics
	from collections import defaultdict
	accuracy_by_kind = defaultdict(list)
	for row in rows:
		tags = row.get("tags", "").split(",") if row.get("tags") else []
		kind = "normal"
		for tag in tags:
			if tag.strip() in ["case", "reexport", "test", "vendor", "nearname"]:
				kind = tag.strip()
				break
		accuracy_by_kind[kind].append(1 if row.get("passed") else 0)
	
	summary = {
		"run_id": run_id,
		"num_tasks": len(rows),
		"accuracy_localization": sum(1 for r in rows if r.get("passed")) / max(len(rows), 1),
		"faithfulness_rate": sum(1 for r in rows if r.get("faithful") == 1) / max(len(rows), 1),
		"line_iou_avg": sum(r.get("line_iou_avg", 0.0) for r in rows) / max(len(rows), 1),
		"p50_latency_ms": p50,
		"p95_latency_ms": p95,
		"avg_tokens_in": avg_tokens_in,
		"avg_tokens_out": avg_tokens_out,
		"avg_tokens_total": avg_tokens_in + avg_tokens_out,
		"canary_pass": gate_code == 0,
		"accuracy_by_variant_kind": {kind: sum(acc) / max(len(acc), 1) for kind, acc in accuracy_by_kind.items()},
	}
	# Reports
	from .common import ensure_dirs
	run_dir = os.path.join(cfg.paths.reports, run_id)
	ensure_dirs(run_dir)
	import csv
	with open(os.path.join(run_dir, "w1_by_task.csv"), "w", newline="", encoding="utf-8") as f:
		keys = [
			"task_id","path_match","line_iou_avg","line_iou_min","symbol_match","symbol_presence_rate","faithful","faithfulness_reason","label_primary","label_secondary","latency_ms","tokens_in","tokens_out","context_tokens","passed"
		]
		w = csv.DictWriter(f, fieldnames=keys)
		w.writeheader()
		for r in rows:
			w.writerow({k: r.get(k) for k in keys})
	write_reports(cfg.paths.reports, run_id, rows, summary, cfg.run.report_format)
	append_registry(cfg.paths.registry, summary)
	_print_cli_summary(rows)


if __name__ == "__main__":
	main()

