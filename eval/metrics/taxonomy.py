from typing import Dict, Any, List

LABEL_WRONG_PATH = "wrong_path"
LABEL_MISSING_PATH = "missing_path"
LABEL_WRONG_LINE = "wrong_line"
LABEL_SYMBOL_ABSENT = "symbol_absent"
LABEL_CITE_MISSING = "cite_missing"
LABEL_CITE_IRRELEVANT = "cite_irrelevant"
LABEL_REEXPORT_ONLY = "reexport_only"
LABEL_VENDOR_HIT = "vendor_hit"
LABEL_TEST_INSTEAD_OF_SRC = "test_instead_of_src"
LABEL_LATENCY_SLO = "latency_slo"
LABEL_COST_SLO = "cost_slo"

# W2 labels
LABEL_ANCHORS_MISSING = "anchors_missing"
LABEL_ANCHORS_UNFAITHFUL = "anchors_unfaithful"
LABEL_FORBIDDEN_CLAIM = "forbidden_claim"
LABEL_OK = "ok"


def map_labels(pred: Dict[str, Any], gold: Dict[str, Any], localization: Dict[str, Any], faithfulness: Dict[str, Any], thresholds: Dict[str, Any]) -> Dict[str, Any]:
	primary = None
	secondary: List[str] = []
	ppaths = set(pred.get("answer", {}).get("paths", []) or [])
	gpaths = set(gold.get("paths", []) or [])
	if not ppaths:
		primary = primary or LABEL_MISSING_PATH
	elif gpaths and ppaths != gpaths:
		primary = primary or LABEL_WRONG_PATH
	# Lines
	if localization.get("line_iou_min", 1.0) < thresholds.get("line_iou_min", 0.6):
		primary = primary or LABEL_WRONG_LINE
	# Symbol
	if localization.get("symbol_match") == 0:
		secondary.append(LABEL_SYMBOL_ABSENT)
	# Faithfulness
	reason = faithfulness.get("faithfulness_reason")
	if reason == "cite_missing":
		secondary.append(LABEL_CITE_MISSING)
	elif reason == "cite_irrelevant":
		secondary.append(LABEL_CITE_IRRELEVANT)
	# Heuristics
	if any("/vendor/" in p or "third_party" in p for p in ppaths):
		secondary.append(LABEL_VENDOR_HIT)
	if any("/test" in p or "/tests/" in p for p in ppaths):
		secondary.append(LABEL_TEST_INSTEAD_OF_SRC)
	# SLOs
	lat = (pred.get("timing", {}) or {}).get("latency_ms", 0)
	if thresholds and lat and lat > thresholds.get("p95_latency_ms", 1e9):
		secondary.append(LABEL_LATENCY_SLO)
	tok = pred.get("tokens", {}) or {}
	if tok.get("in", 0) > thresholds.get("max_tokens_in", 1e9) or tok.get("out", 0) > thresholds.get("max_tokens_out", 1e9) or tok.get("context", 0) > thresholds.get("max_context_tokens", 1e9):
		secondary.append(LABEL_COST_SLO)
	default_primary = LABEL_OK if gpaths else LABEL_MISSING_PATH
	return {"primary": primary or default_primary, "secondary": secondary}


def map_w2_labels(forbidden_hit: bool, anchors_found: int, anchors_faithful: int, anchors_required: int, slo: Dict[str, Any], pred: Dict[str, Any]) -> Dict[str, Any]:
	primary = LABEL_OK
	secondary: List[str] = []
	if anchors_found < anchors_required:
		primary = LABEL_ANCHORS_MISSING
	elif anchors_faithful < anchors_required:
		primary = LABEL_ANCHORS_UNFAITHFUL
	if forbidden_hit:
		primary = LABEL_FORBIDDEN_CLAIM
	# SLOs
	lat = (pred.get("timing", {}) or {}).get("latency_ms", 0)
	if slo and lat and lat > slo.get("p95_latency_ms", 1e9):
		secondary.append(LABEL_LATENCY_SLO)
	tok = pred.get("tokens", {}) or {}
	if tok.get("in", 0) > slo.get("max_tokens_in", 1e9) or tok.get("out", 0) > slo.get("max_tokens_out", 1e9) or tok.get("context", 0) > slo.get("max_context_tokens", 1e9):
		secondary.append(LABEL_COST_SLO)
	return {"primary": primary, "secondary": secondary}

