"""Observability and tracing for poker model evaluation."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ActionTrace:
    """Full trace of a single action decision."""
    timestamp: str
    hand_id: int
    street: str
    model_name: str

    # Game state
    hole_cards: Tuple[str, str]
    board: List[str]
    pot: int
    to_call: int
    stack: int
    position: str

    # Model I/O
    prompt: str
    raw_response: str
    thinking: str

    # Parsing result
    parsed_action: str
    parsed_amount: Optional[int]
    parse_method: str  # "tag" | "regex_fallback" | "default_fallback"
    parse_error: Optional[str]

    # Execution
    executed_action: str
    fallback_used: bool

    # Performance
    latency_ms: float
    tokens_input: int
    tokens_output: int


@dataclass
class ModelObservability:
    """Aggregated observability metrics for a model."""
    model_name: str
    total_actions: int = 0

    # Parsing quality
    valid_tag_parses: int = 0
    regex_fallback_parses: int = 0
    default_fallback_parses: int = 0

    # Action execution
    action_execution_failures: int = 0

    # Response quality
    empty_responses: int = 0
    timeout_errors: int = 0
    api_errors: int = 0

    # Action distribution
    fold_count: int = 0
    check_count: int = 0
    call_count: int = 0
    raise_count: int = 0
    all_in_count: int = 0

    # Performance
    latencies: List[float] = field(default_factory=list)
    total_tokens_input: int = 0
    total_tokens_output: int = 0

    @property
    def parse_error_rate(self) -> float:
        """Rate of actions that required fallback parsing."""
        if self.total_actions == 0:
            return 0.0
        return (self.regex_fallback_parses + self.default_fallback_parses) / self.total_actions

    @property
    def fallback_execution_rate(self) -> float:
        """Rate of actions that fell back during execution."""
        if self.total_actions == 0:
            return 0.0
        return self.action_execution_failures / self.total_actions

    @property
    def malformed_responses(self) -> int:
        """Total malformed responses."""
        return self.empty_responses + self.default_fallback_parses

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def p50_latency_ms(self) -> float:
        """Median latency."""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        mid = len(sorted_lat) // 2
        return sorted_lat[mid]

    @property
    def p99_latency_ms(self) -> float:
        """99th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "total_actions": self.total_actions,
            "parsing": {
                "valid_tag_parses": self.valid_tag_parses,
                "regex_fallback_parses": self.regex_fallback_parses,
                "default_fallback_parses": self.default_fallback_parses,
                "parse_error_rate": round(self.parse_error_rate, 4),
            },
            "execution": {
                "action_execution_failures": self.action_execution_failures,
                "fallback_execution_rate": round(self.fallback_execution_rate, 4),
            },
            "response_quality": {
                "empty_responses": self.empty_responses,
                "timeout_errors": self.timeout_errors,
                "api_errors": self.api_errors,
                "malformed_responses": self.malformed_responses,
            },
            "action_distribution": {
                "fold": self.fold_count,
                "check": self.check_count,
                "call": self.call_count,
                "raise": self.raise_count,
                "all_in": self.all_in_count,
            },
            "performance": {
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "p50_latency_ms": round(self.p50_latency_ms, 2),
                "p99_latency_ms": round(self.p99_latency_ms, 2),
                "total_tokens_input": self.total_tokens_input,
                "total_tokens_output": self.total_tokens_output,
            },
        }


class ObservabilityCollector:
    """Collects traces and computes metrics for model evaluation."""

    def __init__(self, output_dir: str = "tournament_results"):
        self.output_dir = Path(output_dir)
        self.traces_dir = self.output_dir / "observability" / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self.traces: Dict[str, List[ActionTrace]] = {}  # model_name -> traces
        self.metrics: Dict[str, ModelObservability] = {}  # model_name -> metrics

    def record_action(
        self,
        model_name: str,
        hand_id: int,
        street: str,
        hole_cards: Tuple[str, str],
        board: List[str],
        pot: int,
        to_call: int,
        stack: int,
        position: str,
        prompt: str,
        raw_response: str,
        thinking: str,
        parsed_action: str,
        parsed_amount: Optional[int],
        parse_method: str,
        parse_error: Optional[str],
        executed_action: str,
        fallback_used: bool,
        latency_ms: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> None:
        """Record a single action trace and update metrics."""
        # Create trace
        trace = ActionTrace(
            timestamp=datetime.now().isoformat(),
            hand_id=hand_id,
            street=street,
            model_name=model_name,
            hole_cards=hole_cards,
            board=board,
            pot=pot,
            to_call=to_call,
            stack=stack,
            position=position,
            prompt=prompt,
            raw_response=raw_response,
            thinking=thinking,
            parsed_action=parsed_action,
            parsed_amount=parsed_amount,
            parse_method=parse_method,
            parse_error=parse_error,
            executed_action=executed_action,
            fallback_used=fallback_used,
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )

        # Store trace
        if model_name not in self.traces:
            self.traces[model_name] = []
        self.traces[model_name].append(trace)

        # Update metrics
        if model_name not in self.metrics:
            self.metrics[model_name] = ModelObservability(model_name=model_name)
        metrics = self.metrics[model_name]

        metrics.total_actions += 1
        metrics.latencies.append(latency_ms)
        metrics.total_tokens_input += tokens_input
        metrics.total_tokens_output += tokens_output

        # Parsing quality
        if parse_method == "tag":
            metrics.valid_tag_parses += 1
        elif parse_method.startswith("regex"):
            metrics.regex_fallback_parses += 1
        elif parse_method == "default":
            metrics.default_fallback_parses += 1

        # Response quality
        if not raw_response or raw_response.strip() == "":
            metrics.empty_responses += 1
        if parse_error and "timeout" in parse_error.lower():
            metrics.timeout_errors += 1
        if parse_error and "api" in parse_error.lower():
            metrics.api_errors += 1

        # Execution
        if fallback_used:
            metrics.action_execution_failures += 1

        # Action distribution
        action_lower = executed_action.lower()
        if action_lower == "fold":
            metrics.fold_count += 1
        elif action_lower == "check":
            metrics.check_count += 1
        elif action_lower == "call":
            metrics.call_count += 1
        elif action_lower == "raise":
            metrics.raise_count += 1
        elif action_lower == "all_in":
            metrics.all_in_count += 1

    def write_traces(self, matchup_id: str) -> None:
        """Write traces to JSONL files."""
        for model_name, traces in self.traces.items():
            safe_name = model_name.replace("/", "_").replace(" ", "_")
            filepath = self.traces_dir / f"{safe_name}_{matchup_id}.jsonl"

            with open(filepath, "w") as f:
                for trace in traces:
                    # Convert dataclass to dict, handling tuples
                    trace_dict = asdict(trace)
                    trace_dict["hole_cards"] = list(trace.hole_cards)
                    f.write(json.dumps(trace_dict) + "\n")

    def get_metrics(self, model_name: str) -> Optional[ModelObservability]:
        """Get metrics for a specific model."""
        return self.metrics.get(model_name)

    def get_all_metrics(self) -> Dict[str, ModelObservability]:
        """Get metrics for all models."""
        return self.metrics

    def export_metrics(self) -> None:
        """Export aggregated metrics to JSON."""
        metrics_path = self.output_dir / "observability" / "model_metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)

        data = {name: m.to_dict() for name, m in self.metrics.items()}
        with open(metrics_path, "w") as f:
            json.dump(data, f, indent=2)

    def export_error_summary(self) -> None:
        """Export error summary to CSV."""
        csv_path = self.output_dir / "observability" / "error_summary.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, "w") as f:
            f.write("Model,Actions,ValidParse,RegexFallback,DefaultFallback,ErrorRate,EmptyResp,Timeouts\n")
            for name, m in self.metrics.items():
                f.write(f"{name},{m.total_actions},{m.valid_tag_parses},{m.regex_fallback_parses},"
                        f"{m.default_fallback_parses},{m.parse_error_rate:.4f},"
                        f"{m.empty_responses},{m.timeout_errors}\n")

    def print_summary(self) -> None:
        """Print human-readable summary."""
        print("\n" + "=" * 70)
        print("OBSERVABILITY SUMMARY")
        print("=" * 70)

        for name, m in self.metrics.items():
            print(f"\n{name}:")
            print(f"  Total actions: {m.total_actions}")
            print(f"  Parse error rate: {m.parse_error_rate:.1%}")
            print(f"  Fallback execution rate: {m.fallback_execution_rate:.1%}")
            print(f"  Avg latency: {m.avg_latency_ms:.0f}ms (p99: {m.p99_latency_ms:.0f}ms)")
            print(f"  Action distribution: fold={m.fold_count}, check={m.check_count}, "
                  f"call={m.call_count}, raise={m.raise_count}, all_in={m.all_in_count}")

    def clear(self) -> None:
        """Clear all traces and metrics."""
        self.traces = {}
        self.metrics = {}
