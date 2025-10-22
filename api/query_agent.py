import argparse
import json
import sys
import time
from datetime import datetime, timezone


def _now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _to_text(result: dict) -> str:
	ans = result.get("answer", {}) or {}
	paths = ans.get("paths", []) or []
	ranges = ans.get("line_ranges", []) or []
	quotes = ans.get("quotes", []) or []
	# Build a concise one-liner
	if paths:
		p0 = paths[0]
		rng = ranges[0] if ranges else None
		rng_txt = f" lines {rng[0]}–{rng[1]}" if rng else ""
		q0 = quotes[0] if quotes else ""
		return f"Most relevant location: {p0}{rng_txt}. Quote: {q0 or 'n/a'}."
	return "No relevant location found."


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--task_file", required=True)
	parser.add_argument("--format", choices=["json","text"], default="json")
	args = parser.parse_args()

	try:
		with open(args.task_file, "r", encoding="utf-8") as f:
			task = json.load(f)
	except Exception as e:
		print(json.dumps({"error": f"failed_to_read_task:{e}"}), file=sys.stdout)
		return 1

	start_ts = _now_iso()
	start = time.time()

	# Minimal, deterministic mock answer
	answer = {
		"paths": task.get("acceptance_criteria", {}).get("paths", []) or task.get("inputs", {}).get("paths", []),
		"line_ranges": task.get("acceptance_criteria", {}).get("line_ranges", []),
		"quotes": ["mock quote"],
		"rationale": "mock rationale"
	}
	citations = []
	for p in answer.get("paths", [])[:1]:
		citations.append({"path": p, "start": 1, "end": 5})

	latency_ms = int((time.time() - start) * 1000)
	result = {
		"id": task.get("id", "unknown"),
		"answer": answer,
		"citations": citations,
		"timing": {
			"latency_ms": latency_ms,
			"started_at": start_ts,
			"ended_at": _now_iso()
		},
		"tokens": {
			"in": 50,
			"out": 20,
			"context": 0
		},
		"tool_calls": [{"name": "search", "args": {"q": "mock"}}]
	}
	if args.format == "text":
		print(_to_text(result))
		return 0
	print(json.dumps(result), file=sys.stdout)
	return 0


if __name__ == "__main__":
	sys.exit(main())

