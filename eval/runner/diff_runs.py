import os
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple

from .config import get_config


def _load_registry_df(registry_dir: str) -> Optional[Any]:
	"""Load registry as DataFrame, fallback to CSV if parquet missing."""
	try:
		import pandas as pd
		import pyarrow as pa  # noqa: F401
		path = os.path.join(registry_dir, "runs.parquet")
		if os.path.exists(path):
			return pd.read_parquet(path)
	except Exception:
		pass
	try:
		import pandas as pd
		csv_path = os.path.join(registry_dir, "runs.csv")
		if os.path.exists(csv_path):
			return pd.read_csv(csv_path)
	except Exception:
		pass
	return None


def _load_summary(reports_dir: str, run_id: str) -> Optional[Dict[str, Any]]:
	"""Load summary.json if exists."""
	path = os.path.join(reports_dir, run_id, "summary.json")
	if os.path.exists(path):
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	return None


def _get_run_row(df: Any, run_id: str) -> Optional[Dict[str, Any]]:
	"""Extract row for run_id from DataFrame."""
	if df is None:
		return None
	mask = df["run_id"] == run_id
	if not mask.any():
		return None
	return df[mask].iloc[0].to_dict()


def _format_delta(before: float, after: float, is_percent: bool = False) -> str:
	"""Format delta with ▲/▼ and +/-."""
	diff = after - before
	if abs(diff) < 0.001:
		return "="
	sign = "▲" if diff > 0 else "▼"
	unit = "pp" if is_percent else ""
	return f"{sign} {diff:+.1f}{unit}"


def _format_trend(values: List[float], is_percent: bool = False) -> str:
	"""Simple text sparkline for trend."""
	if len(values) < 2:
		return "="
	first, last = values[0], values[-1]
	diff = last - first
	if abs(diff) < 0.001:
		return "="
	unit = "pp" if is_percent else ""
	return f"{diff:+.1f}{unit}"


def _cross_validate(registry_row: Dict[str, Any], summary: Optional[Dict[str, Any]], run_id: str) -> List[str]:
	"""Cross-check registry vs summary.json; return warnings."""
	warnings: List[str] = []
	if not summary:
		return warnings
	# Check W1 aggregates
	for key in ["accuracy_localization", "p95_latency_ms", "avg_tokens_in", "avg_tokens_out"]:
		reg_val = registry_row.get(key)
		sum_val = summary.get(key)
		if reg_val is not None and sum_val is not None and abs(reg_val - sum_val) > 0.01:
			warnings.append(f"{run_id}: {key} mismatch: reg={reg_val}, sum={sum_val}")
	return warnings


def compare_runs(before_id: str, after_id: str, last_n: Optional[int] = None) -> None:
	"""Compare two runs and optionally show trends."""
	cfg = get_config()
	df = _load_registry_df(cfg.paths.registry)
	if df is None:
		print("No registry found. Run evaluations first.")
		return
	before_row = _get_run_row(df, before_id)
	after_row = _get_run_row(df, after_id)
	if before_row is None:
		print(f"Run {before_id} not found in registry.")
		return
	if after_row is None:
		print(f"Run {after_id} not found in registry.")
		return
	# Cross-validate
	before_summary = _load_summary(cfg.paths.reports, before_id)
	after_summary = _load_summary(cfg.paths.reports, after_id)
	warnings = []
	warnings.extend(_cross_validate(before_row, before_summary, before_id))
	warnings.extend(_cross_validate(after_row, after_summary, after_id))
	if warnings:
		print("Warnings:")
		for w in warnings:
			print(f"  {w}")
		print()
	# Print comparison table
	print(f"Run Comparison: {before_id} → {after_id}")
	print("-" * 50)
	# W1 metrics
	w1_metrics = [
		("W1 Accuracy", "accuracy_localization", True),
		("W1 Faithfulness", "faithfulness_rate", True),
		("W1 IoU Avg", "line_iou_avg", False),
		("W1 p95 Latency", "p95_latency_ms", False),
		("W1 Avg Tokens", "avg_tokens_total", False),
		("W1 Canary OK", "canary_pass", False),
	]
	for name, key, is_percent in w1_metrics:
		before_val = before_row.get(key)
		after_val = after_row.get(key)
		if before_val is None or after_val is None:
			print(f"{name:20} | N/A")
			continue
		delta = _format_delta(before_val, after_val, is_percent)
		print(f"{name:20} | {before_val:6.2f} → {after_val:6.2f} {delta}")
	# W2 metrics
	w2_metrics = [
		("W2 Pass Overall", "w2_pass_overall", True),
		("W2 Anchor Coverage", "w2_anchor_coverage_mean", True),
		("W2 Anchor Faithful", "w2_anchor_faithful_rate_mean", True),
		("W2 p95 Latency", "w2_p95_latency_ms", False),
		("W2 Avg Tokens", "w2_avg_tokens", False),
	]
	for name, key, is_percent in w2_metrics:
		before_val = before_row.get(key)
		after_val = after_row.get(key)
		if before_val is None or after_val is None:
			print(f"{name:20} | N/A")
			continue
		delta = _format_delta(before_val, after_val, is_percent)
		print(f"{name:20} | {before_val:6.2f} → {after_val:6.2f} {delta}")
	# Conclusion
	conclusion_parts = []
	if "accuracy_localization" in before_row and "accuracy_localization" in after_row:
		acc_delta = after_row["accuracy_localization"] - before_row["accuracy_localization"]
		conclusion_parts.append(f"W1 accuracy {'▲' if acc_delta > 0 else '▼'} {acc_delta:+.1f}pp")
	if "canary_pass" in after_row:
		conclusion_parts.append("canaries OK" if after_row["canary_pass"] else "canaries FAIL")
	if "p95_latency_ms" in before_row and "p95_latency_ms" in after_row:
		lat_delta = after_row["p95_latency_ms"] - before_row["p95_latency_ms"]
		conclusion_parts.append(f"p95 latency {'▼' if lat_delta < 0 else '▲'} {lat_delta:+.0f}ms")
	print(f"\nConclusion: {'; '.join(conclusion_parts)}.")
	# Trends if requested
	if last_n and last_n > 1:
		print(f"\nTrends (last {last_n} runs):")
		print("-" * 30)
		# Sort by run_id (assuming it's sortable) and take last N
		recent = df.tail(last_n)
		for name, key, is_percent in w1_metrics + w2_metrics:
			values = recent[key].dropna().tolist()
			if not values:
				continue
			trend = _format_trend(values, is_percent)
			print(f"{name:20} | {trend}")


def main() -> None:
	ap = argparse.ArgumentParser(description="Compare evaluation runs")
	ap.add_argument("--before", required=True, help="Before run_id")
	ap.add_argument("--after", required=True, help="After run_id")
	ap.add_argument("--last", type=int, help="Show trends over last N runs")
	args = ap.parse_args()
	compare_runs(args.before, args.after, args.last)


if __name__ == "__main__":
	main()