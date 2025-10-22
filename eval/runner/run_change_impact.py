import os
import argparse
from typing import Dict, Any, List, Tuple

from .config import get_config
from .common import load_tasks_for_workflow, load_goldens_jsonl, call_sut, write_reports, new_run_id, ensure_dirs
from ..metrics.faithfulness import evaluate_faithfulness
from ..metrics.localization import line_iou_scores
from ..metrics.taxonomy import map_w2_labels


def _anchor_line_iou(cited_ranges: List[Tuple[int, int]], quote_range: Tuple[int, int]) -> float:
	# IoU between the quote range and best cited range
	res = line_iou_scores([quote_range], cited_ranges)
	return res["min"]


def _deterministic_core(task: Dict[str, Any], pred: Dict[str, Any], golden: Dict[str, Any], cfg) -> Dict[str, Any]:
	ans = pred.get("answer", {}) or {}
	citations = pred.get("citations", []) or []
	faith = evaluate_faithfulness(ans, citations)
	required = golden.get("required_anchors", []) or []
	anchors_found = 0
	anchors_faithful = 0
	for req in required:
		path = req.get("path")
		symbol = req.get("symbol")
		# find citation for this path
		cited = [c for c in citations if c.get("path") == path]
		if not cited:
			continue
		anchors_found += 1
		# symbol check in rationale text
		if symbol and symbol not in (ans.get("rationale", "")):
			continue
		# try to match any example quote line range
		examples = golden.get("example_quotes", [])
		examples_for_path = [q for q in examples if q.get("path") == path]
		faith_ok = False
		for ex in examples_for_path:
			qr = (int(ex.get("start", 0)), int(ex.get("end", 0)))
			for c in cited:
				cr = (int(c.get("start", 0)), int(c.get("end", 0)))
				if _anchor_line_iou([cr], qr) >= cfg.thresholds.w1.line_iou_min:
					faith_ok = True
					break
			if faith_ok:
				break
		if faith_ok:
			anchors_faithful += 1
	# Forbidden claims
	forbidden = False
	for claim in (golden.get("forbidden_claims") or []):
		if claim and (claim in (ans.get("rationale", ""))):
			forbidden = True
			break
	anchors_required = len(required)
	coverage = (anchors_found / anchors_required) if anchors_required else 0.0
	faith_rate = (anchors_faithful / anchors_required) if anchors_required else 0.0
	return {
		"faith": faith,
		"anchors_required": anchors_required,
		"anchors_found": anchors_found,
		"anchor_coverage": coverage,
		"anchors_faithful": anchors_faithful,
		"anchor_faithful_rate": faith_rate,
		"forbidden_hit": 1 if forbidden else 0,
	}


def judge_evaluate(answer: Dict[str, Any], golden: Dict[str, Any], checklist: List[str], cfg) -> Dict[str, Any]:
	if not cfg.judge.enabled_for_w2:
		# Deterministic verdict only
		return {"used": False, "pass": True, "reasons": ["stub_disabled"]}
	# TODO: plug real LLM judge call here using cfg.judge.model_name
	# For now, simulate: pass if no forbidden and coverage faithful
	return {"used": True, "pass": True, "reasons": ["stub_pass"]}


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--suite", choices=["w2","all"], default="w2")
	args = ap.parse_args()
	cfg = get_config()
	# Load W2 tasks/goldens
	tasks = load_tasks_for_workflow(os.path.join(cfg.paths.scenarios, "w2_change_impact"))
	goldens = load_goldens_jsonl(os.path.join(cfg.paths.goldens, "w2_change_impact"))
	run_id = new_run_id()
	rows: List[Dict[str, Any]] = []
	for task in tasks:
		gold = goldens.get(task.get("id"), {})
		pred = call_sut(task, cfg.sut_cli.timeout_s, cfg.sut_cli.cmd, cfg.sut_cli.extra_args)
		core = _deterministic_core(task, pred, gold, cfg)
		judge = judge_evaluate(pred.get("answer", {}) or {}, gold, (gold.get("checklist") or []), cfg)
		# overall flags
		faithful_overall = 1 if (core["anchor_faithful_rate"] == 1.0 and core["forbidden_hit"] == 0 and (core["faith"]["faithful"] == 1 or not cfg.thresholds.w1.faithfulness_required)) else 0
		labels = map_w2_labels(
			forbidden_hit=bool(core["forbidden_hit"]),
			anchors_found=core["anchors_found"],
			anchors_faithful=core["anchors_faithful"],
			anchors_required=core["anchors_required"],
			slo={
				"p95_latency_ms": cfg.latency_cost_slo.p95_latency_ms,
				"max_tokens_in": cfg.latency_cost_slo.max_tokens_in,
				"max_tokens_out": cfg.latency_cost_slo.max_tokens_out,
				"max_context_tokens": cfg.latency_cost_slo.max_context_tokens,
			},
			pred=pred,
		)
		row = {
			"task_id": task.get("id"),
			"anchors_required": core["anchors_required"],
			"anchors_found": core["anchors_found"],
			"anchor_coverage": core["anchor_coverage"],
			"anchors_faithful": core["anchors_faithful"],
			"anchor_faithful_rate": core["anchor_faithful_rate"],
			"forbidden_hit": core["forbidden_hit"],
			"judge_used": 1 if judge["used"] else 0,
			"judge_pass": 1 if judge["pass"] else 0,
			"faithful_overall": faithful_overall,
			"label_primary": labels["primary"],
			"label_secondary": ",".join(labels.get("secondary", [])),
			"latency_ms": (pred.get("timing", {}) or {}).get("latency_ms", 0),
			"tokens_in": (pred.get("tokens", {}) or {}).get("in", 0),
			"tokens_out": (pred.get("tokens", {}) or {}).get("out", 0),
		}
		rows.append(row)
	# Reports
	run_dir = os.path.join(cfg.paths.reports, run_id)
	ensure_dirs(run_dir)
	import csv
	with open(os.path.join(run_dir, "w2_by_task.csv"), "w", newline="", encoding="utf-8") as f:
		keys = [
			"task_id","anchors_required","anchors_found","anchor_coverage","anchors_faithful","anchor_faithful_rate","forbidden_hit","judge_used","judge_pass","faithful_overall","label_primary","label_secondary","latency_ms","tokens_in","tokens_out"
		]
		w = csv.DictWriter(f, fieldnames=keys)
		w.writeheader()
		for r in rows:
			w.writerow({k: r.get(k) for k in keys})
	# Summary block
	def _mean(name: str) -> float:
		return (sum(r.get(name, 0.0) for r in rows) / max(len(rows), 1)) if rows else 0.0
	from statistics import median
	latencies = [r.get("latency_ms", 0) for r in rows]
	p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
	summary = {
		"run_id": run_id,
		"w2": {
			"anchor_coverage_mean": _mean("anchor_coverage"),
			"anchor_faithful_rate_mean": _mean("anchor_faithful_rate"),
			"pass_det_core": sum(1 for r in rows if r.get("anchor_faithful_rate") == 1.0 and r.get("forbidden_hit") == 0) / max(len(rows), 1),
			"pass_overall": sum(1 for r in rows if r.get("faithful_overall") == 1) / max(len(rows), 1),
			"p95_latency_ms": p95,
			"avg_tokens": _mean("tokens_in") + _mean("tokens_out"),
		}
	}
	# Persist summary alongside W1; append registry (additive schema)
	# We reuse write_reports to produce JSON/Parquet by_task as well if wanted by caller elsewhere.
	with open(os.path.join(run_dir, "w2_summary.json"), "w", encoding="utf-8") as f:
		import json
		json.dump(summary, f, indent=2)
	# Minimal registry append: flatten a few fields
	from .common import append_registry
	append_registry(cfg.paths.registry, {
		"run_id": run_id,
		"w2_anchor_coverage_mean": summary["w2"]["anchor_coverage_mean"],
		"w2_anchor_faithful_rate_mean": summary["w2"]["anchor_faithful_rate_mean"],
		"w2_pass_overall": summary["w2"]["pass_overall"],
		"w2_p95_latency_ms": summary["w2"]["p95_latency_ms"],
		"w2_avg_tokens": summary["w2"]["avg_tokens"],
	})


if __name__ == "__main__":
	main()

