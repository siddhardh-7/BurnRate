"""
ChaosController — injectable failure modes for the demo app.
Each scenario causes a different cost pathology that Burnrate/Cost Guard catches.
"""

from __future__ import annotations

import random


class ChaosController:
    SCENARIOS = {
        "retry_loop": "Researcher retries every call 8-12 times (cost ×10)",
        "model_misroute": "Cheap tasks routed to expensive model (cost ×20)",
        "prompt_bloat": "Context accumulates without summarization (cost grows 5× per call)",
        "cache_miss_storm": "Slight prompt variations defeat Anthropic caching (cache savings lost)",
        None: "Normal operation",
    }

    def __init__(self) -> None:
        self.active_scenario: str | None = None

    def activate(self, scenario: str) -> None:
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario!r}. Valid: {list(self.SCENARIOS)}")
        self.active_scenario = scenario

    def deactivate(self) -> None:
        self.active_scenario = None

    def retry_count(self) -> int:
        """How many times researcher should retry (retry_loop scenario)."""
        return random.randint(8, 12) if self.active_scenario == "retry_loop" else 1
