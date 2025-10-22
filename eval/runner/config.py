import os
import dataclasses
import typing as t
import json

import yaml


@dataclasses.dataclass
class Paths:
	scenarios: str
	goldens: str
	canary: str
	judges: str
	reports: str
	registry: str


@dataclasses.dataclass
class W1Thresholds:
	path_match_required: bool = True
	line_iou_min: float = 0.6
	require_symbol_match: bool = True
	faithfulness_required: bool = True


@dataclasses.dataclass
class CanaryThresholds:
	require_100_percent: bool = True


@dataclasses.dataclass
class Thresholds:
	w1: W1Thresholds
	canary: CanaryThresholds


@dataclasses.dataclass
class Judge:
	enabled_for_w2: bool = False
	model_name: str = ""
	max_tokens: int = 512
	temperature: float = 0.0


@dataclasses.dataclass
class LatencyCostSLO:
	p95_latency_ms: int = 5000
	max_tokens_in: int = 20000
	max_tokens_out: int = 4000
	max_context_tokens: int = 50000


@dataclasses.dataclass
class RunCfg:
	seed: int = 7
	fail_fast_on_canary: bool = True
	report_format: t.List[str] = dataclasses.field(default_factory=lambda: ["json", "parquet", "csv"])


@dataclasses.dataclass
class SutCLI:
	cmd: str = "python -m api.query_agent"
	extra_args: t.List[str] = dataclasses.field(default_factory=list)
	timeout_s: int = 60


@dataclasses.dataclass
class Variants:
	enabled: bool = True
	kinds: t.List[str] = dataclasses.field(default_factory=lambda: ["case","reexport","test","vendor","nearname"])
	max_per_source: int = 2


@dataclasses.dataclass
class EvalConfig:
	paths: Paths
	thresholds: Thresholds
	judge: Judge
	latency_cost_slo: LatencyCostSLO
	run: RunCfg
	sut_cli: SutCLI
	variants: Variants

	def to_safe_dict(self) -> dict:
		# For dry-run printing
		return json.loads(json.dumps(dataclasses.asdict(self)))


_CFG_CACHE: t.Optional[EvalConfig] = None


def _apply_env_overrides(cfg: EvalConfig) -> None:
	# Judge
	model = os.getenv("EVAL_MODEL_NAME")
	if model is not None:
		cfg.judge.model_name = model
	p95 = os.getenv("EVAL_P95_LATENCY_MS")
	if p95:
		try:
			cfg.latency_cost_slo.p95_latency_ms = int(p95)
		except ValueError:
			pass
	cmd = os.getenv("EVAL_SUT_CMD")
	if cmd:
		cfg.sut_cli.cmd = cmd
	timeout = os.getenv("EVAL_TIMEOUT_S")
	if timeout:
		try:
			cfg.sut_cli.timeout_s = int(timeout)
		except ValueError:
			pass
	# Paths overrides
	for key in ("SCENARIOS", "GOLDENS", "CANARY", "JUDGES", "REPORTS", "REGISTRY"):
		val = os.getenv(f"EVAL_PATH_{key}")
		if val:
			setattr(cfg.paths, key.lower(), val)


def _validate(cfg: EvalConfig) -> None:
	# Threshold ranges
	if not (0.0 <= cfg.thresholds.w1.line_iou_min <= 1.0):
		raise SystemExit(
			"Set thresholds.w1.line_iou_min ∈ [0,1] in eval/config/config.yaml"
		)
	if cfg.sut_cli.timeout_s <= 0:
		raise SystemExit("Set sut_cli.timeout_s > 0 in eval/config/config.yaml")
	# Paths must exist (scenarios/goldens/canary can be empty but dirs should exist)
	missing = [
		name for name, path in (
			("scenarios", cfg.paths.scenarios),
			("goldens", cfg.paths.goldens),
			("canary", cfg.paths.canary),
			("judges", cfg.paths.judges),
			("reports", cfg.paths.reports),
			("registry", cfg.paths.registry),
		)
		if not os.path.isdir(path)
	]
	if missing:
		raise SystemExit(
			f"Missing required directories: {', '.join(missing)}. Create them under eval/ or update paths.* in eval/config/config.yaml"
		)


def load_config(path: str = "eval/config/config.yaml") -> EvalConfig:
	try:
		with open(path, "r", encoding="utf-8") as f:
			raw = yaml.safe_load(f)
	except FileNotFoundError:
		raise SystemExit(
			"Config file not found at eval/config/config.yaml. Create it (see eval/config/schema.md) or copy a minimal default, e.g.:\n"
			"paths: {scenarios: eval/scenarios, goldens: eval/goldens, canary: eval/canary, judges: eval/judges, reports: eval/reports, registry: eval/registry}\n"
			"thresholds: {w1: {path_match_required: true, line_iou_min: 0.6, require_symbol_match: true, faithfulness_required: true}, canary: {require_100_percent: true}}\n"
			"judge: {enabled_for_w2: false, model_name: '', max_tokens: 512, temperature: 0.0}\n"
			"latency_cost_slo: {p95_latency_ms: 5000, max_tokens_in: 20000, max_tokens_out: 4000, max_context_tokens: 50000}\n"
			"run: {seed: 7, fail_fast_on_canary: true, report_format: ['json','parquet','csv']}\n"
			"sut_cli: {cmd: 'python -m api.query_agent', extra_args: [], timeout_s: 60}"
		)
	paths = Paths(**raw["paths"]) 
	w1 = W1Thresholds(**raw["thresholds"]["w1"]) 
	canary = CanaryThresholds(**raw["thresholds"]["canary"]) 
	thresholds = Thresholds(w1=w1, canary=canary)
	judge = Judge(**raw["judge"]) 
	latency = LatencyCostSLO(**raw["latency_cost_slo"]) 
	run = RunCfg(**raw["run"]) 
	sut = SutCLI(**raw["sut_cli"]) 
	variants = Variants(**raw.get("variants", {}))
	cfg = EvalConfig(paths=paths, thresholds=thresholds, judge=judge, latency_cost_slo=latency, run=run, sut_cli=sut, variants=variants)
	_apply_env_overrides(cfg)
	_validate(cfg)
	return cfg


def get_config(path: str = "eval/config/config.yaml") -> EvalConfig:
	global _CFG_CACHE
	if _CFG_CACHE is None:
		_CFG_CACHE = load_config(path)
	return _CFG_CACHE

