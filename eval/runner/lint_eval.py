import os
import sys
import json
import argparse
from typing import Dict, Any, List

from .config import get_config


def _fail(msgs: List[str]) -> int:
	print("\nFAIL:")
	for m in msgs:
		print(f"- {m}")
	return 1


def _ok() -> int:
	print("\nPASS: no issues found")
	return 0


def check_config() -> List[str]:
	errs: List[str] = []
	cfg = get_config()
	import yaml
	with open("eval/config/config.yaml", "r", encoding="utf-8") as f:
		raw = yaml.safe_load(f)
	allowed = {"paths","thresholds","judge","latency_cost_slo","run","sut_cli","variants"}
	unknown = set(raw.keys()) - allowed
	if unknown:
		errs.append(f"Unknown top-level config keys: {sorted(list(unknown))}")
	return errs


def check_paths(cfg) -> List[str]:
	errs: List[str] = []
	for name in ["scenarios","goldens","canary","judges","reports","registry"]:
		p = getattr(cfg.paths, name)
		if not os.path.isdir(p):
			errs.append(f"Missing directory: paths.{name} -> {p}")
	wf = ".github/workflows/evals.yml"
	if os.path.exists(wf):
		with open(wf, "r", encoding="utf-8") as f:
			text = f.read()
			if "run_localization" not in text or "--suite" not in text:
				errs.append("CI does not call run_localization with --suite")
	else:
		errs.append("Missing CI workflow .github/workflows/evals.yml")
	return errs


def _load_tasks(dirpath: str) -> List[Dict[str, Any]]:
	items: List[Dict[str, Any]] = []
	for root, _, files in os.walk(dirpath):
		for fn in files:
			if fn.endswith((".json",".yaml",".yml")):
				try:
					with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
						items.append(json.load(f))
				except Exception:
					pass
	return items


def _load_goldens(dirpath: str) -> Dict[str, Dict[str, Any]]:
	goldens: Dict[str, Dict[str, Any]] = {}
	for root, _, files in os.walk(dirpath):
		for fn in files:
			if fn.endswith(".jsonl"):
				with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
					for line in f:
						line = line.strip()
						if not line:
							continue
						record = json.loads(line)
						tid = record.get("task_id")
						if tid:
							goldens[tid] = record
	return goldens


def check_scenarios_vs_goldens(cfg) -> List[str]:
	errs: List[str] = []
	w1_tasks = _load_tasks(os.path.join(cfg.paths.scenarios, "w1_localization"))
	w1_goldens = _load_goldens(os.path.join(cfg.paths.goldens, "w1_localization"))
	for t in w1_tasks:
		tid = t.get("id")
		if tid not in w1_goldens:
			errs.append(f"W1 task without golden: {tid}")
	w2_tasks = _load_tasks(os.path.join(cfg.paths.scenarios, "w2_change_impact"))
	w2_goldens = _load_goldens(os.path.join(cfg.paths.goldens, "w2_change_impact"))
	for t in w2_tasks:
		tid = t.get("id")
		if tid not in w2_goldens:
			errs.append(f"W2 task without golden: {tid}")
	canary_tasks = _load_tasks(os.path.join(cfg.paths.canary, "w1_localization"))
	for ct in canary_tasks:
		cid = ct.get("id")
		if cid not in w1_goldens:
			errs.append(f"Canary without matching golden: {cid}")
	return errs


def check_runner_contracts() -> List[str]:
	errs: List[str] = []
	def _scan(path: str, must_have: List[str], must_not: List[str]) -> None:
		if not os.path.exists(path):
			errs.append(f"Missing file: {path}")
			return
		with open(path, "r", encoding="utf-8") as f:
			text = f.read()
			for token in must_have:
				if token not in text:
					errs.append(f"{os.path.basename(path)} missing reference to {token}")
			for token in must_not:
				if token in text:
					errs.append(f"{os.path.basename(path)} contains disallowed hardcode: {token}")
	_scan("eval/runner/run_localization.py", ["get_config("], ["line_iou_min =", "paths = "])
	_scan("eval/runner/run_change_impact.py", ["get_config("], ["line_iou_min =", "paths = "])
	with open("eval/runner/common.py", "r", encoding="utf-8") as f:
		text = f.read()
		for req in ["latency_ms", "tokens", "dry_run_info"]:
			if req not in text:
				errs.append(f"common.py missing '{req}' handling")
	return errs


def check_reports_registry(cfg) -> List[str]:
	errs: List[str] = []
	reports_dir = cfg.paths.reports
	if os.path.isdir(reports_dir):
		subs = [d for d in os.listdir(reports_dir) if os.path.isdir(os.path.join(reports_dir, d))]
		if subs:
			latest = sorted(subs)[-1]
			summary = os.path.join(reports_dir, latest, "summary.json")
			if not os.path.exists(summary):
				errs.append(f"Missing summary.json in {latest}")
			w1csv = os.path.join(reports_dir, latest, "w1_by_task.csv")
			w2csv = os.path.join(reports_dir, latest, "w2_by_task.csv")
			if not (os.path.exists(w1csv) or os.path.exists(w2csv)):
				errs.append(f"Missing *_by_task.csv in {latest}")
	else:
		errs.append("Reports directory missing or empty")
	reg_parquet = os.path.join(cfg.paths.registry, "runs.parquet")
	reg_csv = os.path.join(cfg.paths.registry, "runs.csv")
	if not (os.path.exists(reg_parquet) or os.path.exists(reg_csv)):
		errs.append("Registry file not found (runs.parquet or runs.csv)")
	return errs


def check_judges_and_policy(cfg) -> List[str]:
	errs: List[str] = []
	prompt = os.path.join(cfg.paths.judges, "change_impact", "prompt.md")
	calib = os.path.join(cfg.paths.judges, "change_impact", "calibration.jsonl")
	policy = os.path.join("eval", "policies", "canary_policy.md")
	if not os.path.exists(prompt):
		errs.append("Missing judge prompt.md")
	else:
		with open(prompt, "r", encoding="utf-8") as f:
			text = f.read()
			for req in ["\"pass\"", "\"checks\""]:
				if req not in text:
					errs.append("prompt.md lacks JSON schema snippet")
	if not os.path.exists(calib):
		errs.append("Missing judges/change_impact/calibration.jsonl")
	if not os.path.exists(policy):
		errs.append("Missing eval/policies/canary_policy.md")
	with open("eval/runner/run_change_impact.py", "r", encoding="utf-8") as f:
		text = f.read()
		if "enabled_for_w2" not in text:
			errs.append("run_change_impact.py does not use judge.enabled_for_w2 toggle")
	return errs


def main() -> None:
	ap = argparse.ArgumentParser(description="Eval harness linter (read-only)")
	args = ap.parse_args()
	cfg = get_config()
	errors: List[str] = []
	errors += check_config()
	errors += check_paths(cfg)
	errors += check_scenarios_vs_goldens(cfg)
	errors += check_runner_contracts()
	errors += check_reports_registry(cfg)
	errors += check_judges_and_policy(cfg)
	if errors:
		sys.exit(_fail(errors))
	else:
		sys.exit(_ok())


if __name__ == "__main__":
	main()
