from typing import List, Tuple, Dict, Any, Set
import re


def _iou(a: Tuple[int, int], b: Tuple[int, int]) -> float:
	as_, ae = a
	bs, be = b
	inter = max(0, min(ae, be) - max(as_, bs))
	union = max(ae - as_, 0) + max(be - bs, 0) - inter
	return (inter / union) if union > 0 else 0.0


def path_match_all_only(pred_paths: List[str], golden_paths: List[str]) -> int:
	set_pred: Set[str] = set(pred_paths or [])
	set_gold: Set[str] = set(golden_paths or [])
	return 1 if set_pred == set_gold else 0


def line_iou_scores(pred_line_ranges: List[Tuple[int, int]], golden_line_ranges: List[Tuple[int, int]]) -> Dict[str, Any]:
	if not pred_line_ranges or not golden_line_ranges:
		return {"per_pair": [], "avg": 0.0, "min": 0.0}
	pairs: List[float] = []
	for p in pred_line_ranges:
		best = 0.0
		for g in golden_line_ranges:
			best = max(best, _iou(tuple(p), tuple(g)))
		pairs.append(best)
	avg = sum(pairs) / len(pairs) if pairs else 0.0
	mn = min(pairs) if pairs else 0.0
	return {"per_pair": pairs, "avg": avg, "min": mn}


def _symbol_regex(symbol: str) -> re.Pattern:
	# Escape unless looks like a simple regex already; keep simple/lean
	try:
		return re.compile(symbol)
	except re.error:
		return re.compile(re.escape(symbol))


def symbol_presence(pred_paths: List[str], quotes: List[str], inputs: Dict[str, Any]) -> Dict[str, Any]:
	symbol = (inputs or {}).get("symbol")
	if not symbol:
		return {"symbol_match": 1, "symbol_presence_rate": 1.0}
	pat = _symbol_regex(symbol)
	# We do not have per-path quote mapping; approximate: if any quote contains the symbol, count it for all predicted paths
	if not pred_paths:
		return {"symbol_match": 0, "symbol_presence_rate": 0.0}
	present_any = any(pat.search(q or "") for q in (quotes or []))
	rate = 1.0 if present_any else 0.0
	return {"symbol_match": 1 if rate == 1.0 else 0, "symbol_presence_rate": rate}


def evaluate_localization(pred_answer: Dict[str, Any], golden: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
	pred_paths = pred_answer.get("paths", []) or []
	pred_ranges = pred_answer.get("line_ranges", []) or []
	gold_paths = golden.get("paths", []) or []
	gold_ranges = golden.get("line_ranges", []) or []
	pm = path_match_all_only(pred_paths, gold_paths)
	ious = line_iou_scores(pred_ranges, gold_ranges)
	sym = symbol_presence(pred_paths, pred_answer.get("quotes", []) or [], inputs or {})
	return {
		"path_match": pm,
		"line_iou_avg": ious["avg"],
		"line_iou_min": ious["min"],
		"symbol_match": sym["symbol_match"],
		"symbol_presence_rate": sym["symbol_presence_rate"],
	}

