import os
import json
import argparse
import random
from typing import Dict, Any, List, Tuple
from pathlib import Path


def case_toggle(symbol: str) -> str:
	"""Toggle case in symbol: normalizeUrl ↔ normalizeURL."""
	if not symbol:
		return symbol
	# Simple toggle: if has lowercase, make uppercase; else make lowercase
	if any(c.islower() for c in symbol):
		return symbol.upper()
	else:
		return symbol.lower()


def add_reexport_layer(path: str) -> str:
	"""Add synthetic re-export layer: daemon/foo.c → daemon/index.c."""
	if not path:
		return path
	parts = path.split('/')
	if len(parts) < 2:
		return path
	# Insert index.c before the last part
	dir_part = '/'.join(parts[:-1])
	file_part = parts[-1]
	return f"{dir_part}/index.c"


def test_shadow(path: str) -> str:
	"""Create test shadow: daemon/foo.c → tests/daemon/foo.c."""
	if not path:
		return path
	return f"tests/{path}"


def vendor_shadow(path: str) -> str:
	"""Create vendor shadow: daemon/foo.c → vendor/daemon/foo.c."""
	if not path:
		return path
	return f"vendor/{path}"


def near_name(symbol: str) -> str:
	"""Minimal edit distance: gdm_display_factory_create_display → gdm_display_factory_create_displays."""
	if not symbol:
		return symbol
	# Simple transformations
	if symbol.endswith('_display'):
		return symbol.replace('_display', '_displays')
	elif symbol.endswith('_create'):
		return symbol.replace('_create', '_creates')
	elif symbol.endswith('_init'):
		return symbol.replace('_init', '_inits')
	else:
		# Add 's' at end if not already plural
		return symbol + 's' if not symbol.endswith('s') else symbol


def load_goldens(goldens_dir: str) -> List[Dict[str, Any]]:
	"""Load all goldens from directory."""
	goldens = []
	for root, _, files in os.walk(goldens_dir):
		for file in files:
			if file.endswith('.jsonl'):
				with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
					for line in f:
						line = line.strip()
						if line:
							goldens.append(json.loads(line))
	return goldens


def generate_variant_task(source_golden: Dict[str, Any], variant_id: str, kind: str, method_func) -> Dict[str, Any]:
	"""Generate a variant task card from source golden."""
	source_symbol = source_golden.get('symbol', '')
	modified_symbol = method_func(source_symbol) if source_symbol else ''
	
	# Adjust constraints based on variant kind
	exclude_dirs = ["vendor/", "tests/"]
	if kind == "test":
		exclude_dirs = ["vendor/"]  # Allow tests for test shadow
	elif kind == "vendor":
		exclude_dirs = ["tests/"]   # Allow vendor for vendor shadow
	
	return {
		"id": variant_id,
		"workflow": "w1_localization",
		"inputs": {"symbol": modified_symbol} if modified_symbol else {},
		"constraints": {
			"must_cite": True,
			"exclude_dirs": exclude_dirs
		},
		"acceptance_criteria": {
			"paths": source_golden.get("paths", []),
			"line_ranges": source_golden.get("line_ranges", []),
			"checklist": source_golden.get("checklist", [])
		},
		"tags": ["variant", kind, f"from:{source_golden.get('task_id', '')}"]
	}


def generate_variant_golden(source_golden: Dict[str, Any], variant_id: str, kind: str) -> Dict[str, Any]:
	"""Generate a variant golden (truth unchanged)."""
	return {
		"task_id": variant_id,
		"paths": source_golden.get("paths", []),
		"line_ranges": source_golden.get("line_ranges", []),
		"quotes": source_golden.get("quotes", []),
		"provenance": {
			"from_task": source_golden.get("task_id", ""),
			"method": kind,
			"repo": source_golden.get("provenance", {}).get("repo", ""),
			"commit": source_golden.get("provenance", {}).get("commit", "")
		},
		"notes": "Variant derived; truth unchanged"
	}


def generate_variants(source_dir: str, out_dir: str, limit: int = 10, kinds: List[str] = None) -> None:
	"""Generate variant tasks and goldens."""
	if kinds is None:
		kinds = ["case", "reexport", "test", "vendor", "nearname"]
	
	methods = {
		"case": case_toggle,
		"reexport": add_reexport_layer,
		"test": test_shadow,
		"vendor": vendor_shadow,
		"nearname": near_name
	}
	
	# Load source goldens
	goldens = load_goldens(source_dir)
	if not goldens:
		print(f"No goldens found in {source_dir}")
		return
	
	# Set seed for deterministic generation
	random.seed(42)
	
	# Create output directories
	task_dir = os.path.join(out_dir, "variants")
	golden_dir = os.path.join(source_dir, "variants")
	os.makedirs(task_dir, exist_ok=True)
	os.makedirs(golden_dir, exist_ok=True)
	
	generated = 0
	variant_tasks = []
	variant_goldens = []
	
	for golden in goldens:
		if generated >= limit:
			break
		
		for kind in kinds:
			if generated >= limit:
				break
			
			if kind not in methods:
				continue
			
			variant_id = f"W1-VAR-{generated + 1:03d}"
			method_func = methods[kind]
			
			# Generate variant task
			variant_task = generate_variant_task(golden, variant_id, kind, method_func)
			variant_tasks.append(variant_task)
			
			# Generate variant golden
			variant_golden = generate_variant_golden(golden, variant_id, kind)
			variant_goldens.append(variant_golden)
			
			generated += 1
	
	# Write variant tasks
	for task in variant_tasks:
		task_file = os.path.join(task_dir, f"{task['id']}.json")
		with open(task_file, 'w', encoding='utf-8') as f:
			json.dump(task, f, indent=2)
	
	# Write variant goldens
	golden_file = os.path.join(golden_dir, "variants.jsonl")
	with open(golden_file, 'w', encoding='utf-8') as f:
		for golden in variant_goldens:
			f.write(json.dumps(golden) + '\n')
	
	print(f"Generated {generated} variants:")
	for kind in kinds:
		count = sum(1 for t in variant_tasks if kind in t.get('tags', []))
		if count > 0:
			print(f"  {kind}: {count}")


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate deterministic variants for W1")
	parser.add_argument("--source", required=True, help="Source goldens directory")
	parser.add_argument("--out", required=True, help="Output scenarios directory")
	parser.add_argument("--limit", type=int, default=10, help="Maximum variants to generate")
	parser.add_argument("--kinds", default="case,reexport,test,vendor,nearname", 
	                   help="Comma-separated list of variant kinds")
	
	args = parser.parse_args()
	kinds = [k.strip() for k in args.kinds.split(',')]
	
	generate_variants(args.source, args.out, args.limit, kinds)


if __name__ == "__main__":
	main()
