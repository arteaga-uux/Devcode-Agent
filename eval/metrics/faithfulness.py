from typing import Dict, Any, List

REASON_OK = "ok"
REASON_CITE_MISSING = "cite_missing"
REASON_CITE_IRRELEVANT = "cite_irrelevant"
REASON_NO_QUOTES = "no_quotes"


def evaluate_faithfulness(answer: Dict[str, Any], citations: List[Dict[str, Any]]) -> Dict[str, Any]:
	paths = answer.get("paths", []) or []
	quotes = answer.get("quotes", []) or []
	if not citations:
		return {"faithful": 0, "faithfulness_reason": REASON_CITE_MISSING}
	c_paths = {c.get("path") for c in citations if c.get("path")}
	if paths and not (set(paths) & c_paths):
		return {"faithful": 0, "faithfulness_reason": REASON_CITE_IRRELEVANT}
	if not quotes:
		return {"faithful": 0, "faithfulness_reason": REASON_NO_QUOTES}
	return {"faithful": 1, "faithfulness_reason": REASON_OK}

