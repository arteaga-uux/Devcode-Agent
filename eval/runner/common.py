import os
import json
import uuid
import time
import subprocess
from typing import Dict, Any, List, Tuple

from .config import load_config


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
	items: List[Dict[str, Any]] = []
	with open(path, "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			items.append(json.loads(line))
	return items


def _glob_files(directory: str, exts: Tuple[str, ...]) -> List[str]:
	paths: List[str] = []
	for root, _, files in os.walk(directory):
		for fn in files:
			if fn.lower().endswith(exts):
				paths.append(os.path.join(root, fn))
	return sorted(paths)


def load_tasks_for_workflow(base_dir: str) -> List[Dict[str, Any]]:
	tasks: List[Dict[str, Any]] = []
	for p in _glob_files(base_dir, (".json", ".yaml", ".yml")):
		if p.endswith(".json"):
			with open(p, "r", encoding="utf-8") as f:
				tasks.append(json.load(f))
		else:
			try:
				import yaml
			except Exception:
				continue
			with open(p, "r", encoding="utf-8") as f:
				tasks.append(yaml.safe_load(f))
	return tasks


def load_goldens_jsonl(base_dir: str) -> Dict[str, Dict[str, Any]]:
	goldens: Dict[str, Dict[str, Any]] = {}
	for p in _glob_files(base_dir, (".jsonl",)):
		for item in _read_jsonl(p):
			tid = item.get("task_id")
			if not tid:
				continue
			goldens[tid] = item
	return goldens


def _normalize_timing_tokens(resp: Dict[str, Any], fallback_latency_ms: int) -> Dict[str, Any]:
	resp.setdefault("timing", {})
	resp["timing"].setdefault("latency_ms", fallback_latency_ms)
	resp.setdefault("tokens", {})
	resp["tokens"].setdefault("in", 0)
	resp["tokens"].setdefault("out", 0)
	resp["tokens"].setdefault("context", 0)
	return resp


def call_sut(task: Dict[str, Any], timeout_s: int, cmd: str, extra_args: List[str]) -> Dict[str, Any]:
	import tempfile
	with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
		json.dump(task, tf)
		tf.flush()
		task_path = tf.name
	argv = cmd.split() + ["--task_file", task_path] + list(extra_args or [])
	start = time.time()
	try:
		proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
	except subprocess.TimeoutExpired:
		return _normalize_timing_tokens({"error": "timeout"}, int((time.time() - start) * 1000))
	latency_ms = int((time.time() - start) * 1000)
	out = proc.stdout.strip()
	try:
		resp = json.loads(out) if out else {}
	except Exception:
		resp = {"raw": out}
	return _normalize_timing_tokens(resp, latency_ms)


def ensure_dirs(*paths: str) -> None:
	for p in paths:
		os.makedirs(p, exist_ok=True)


def new_run_id() -> str:
	return uuid.uuid4().hex[:8]


def write_reports(base: str, run_id: str, by_task: List[Dict[str, Any]], summary: Dict[str, Any], formats: List[str]) -> None:
	run_dir = os.path.join(base, run_id)
	ensure_dirs(run_dir)
	with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
		json.dump(summary, f, indent=2)
	with open(os.path.join(run_dir, "by_task.json"), "w", encoding="utf-8") as f:
		json.dump(by_task, f, indent=2)
	# CSV: naming can be customized by caller as needed
	if "csv" in (formats or []):
		import csv
		csv_path = os.path.join(run_dir, "by_task.csv")
		keys = sorted({k for row in by_task for k in row.keys()})
		with open(csv_path, "w", newline="", encoding="utf-8") as f:
			w = csv.DictWriter(f, fieldnames=keys)
			w.writeheader()
			for row in by_task:
				w.writerow(row)
	# Parquet (optional)
	if "parquet" in (formats or []):
		try:
			import pandas as pd
			import pyarrow as pa  # noqa: F401
			df = pd.DataFrame(by_task)
			df.to_parquet(os.path.join(run_dir, "by_task.parquet"), index=False)
		except Exception:
			pass


def append_registry(registry_dir: str, run_row: Dict[str, Any]) -> None:
	ensure_dirs(registry_dir)
	path = os.path.join(registry_dir, "runs.parquet")
	try:
		import pandas as pd
		import pyarrow as pa  # noqa: F401
		if os.path.exists(path):
			df = pd.read_parquet(path)
			new_df = pd.concat([df, pd.DataFrame([run_row])], ignore_index=True)
			new_df.to_parquet(path, index=False)
		else:
			pd.DataFrame([run_row]).to_parquet(path, index=False)
	except Exception:
		csv_path = os.path.join(registry_dir, "runs.csv")
		import csv
		exists = os.path.exists(csv_path)
		with open(csv_path, "a", newline="", encoding="utf-8") as f:
			w = None
			if not exists:
				w = csv.DictWriter(f, fieldnames=sorted(run_row.keys()))
				w.writeheader()
			else:
				w = csv.DictWriter(f, fieldnames=sorted(run_row.keys()))
			w.writerow(run_row)


def dry_run_info() -> Dict[str, Any]:
	cfg = load_config()
	# Count tasks without invoking SUT
	def _count(dirpath: str) -> int:
		return len(load_tasks_for_workflow(dirpath)) if os.path.isdir(dirpath) else 0
	return {
		"w1_canary": _count(os.path.join(cfg.paths.canary, "w1_localization")),
		"w1": _count(os.path.join(cfg.paths.scenarios, "w1_localization")),
		"w2": _count(os.path.join(cfg.paths.scenarios, "w2_change_impact")),
		"config": cfg.to_safe_dict(),
	}

