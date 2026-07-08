"""
ChaosController — injectable failure modes for the demo app.
Also manages Cost Guard's throttle/restore actions so the self-healing loop is visible.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict


class ChaosController:
    SCENARIOS = {
        "retry_loop": "Researcher retries every call 8-12 times on simulated RateLimit (cost ×10)",
        "model_misroute": "Cheap tasks routed to expensive model (cost ×20)",
        "prompt_bloat": "Context accumulates without summarization (cost grows 5× per call)",
        "cache_miss_storm": "Slight prompt variations defeat Anthropic caching (cache savings lost)",
        None: "Normal operation",
    }

    def __init__(self) -> None:
        self.active_scenario: str | None = None
        # throttle state: agent_id -> max_calls_per_minute (set by Cost Guard action)
        self._throttle: dict[str, int] = {}
        # sliding window call timestamps per agent
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    # ── Chaos injection ───────────────────────────────────────────────────────

    def activate(self, scenario: str) -> None:
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario!r}. Valid: {list(self.SCENARIOS)}")
        self.active_scenario = scenario

    def deactivate(self) -> None:
        self.active_scenario = None

    def retry_count(self) -> int:
        """How many LLM attempts researcher makes (retry_loop scenario)."""
        return random.randint(8, 12) if self.active_scenario == "retry_loop" else 1

    # ── Cost Guard throttle actions ───────────────────────────────────────────

    def throttle_agent(self, agent_id: str, max_calls_per_minute: int = 2) -> None:
        self._throttle[agent_id] = max_calls_per_minute

    def restore_all(self) -> None:
        self._throttle.clear()
        self._timestamps.clear()

    def record_call(self, agent_id: str) -> None:
        self._timestamps[agent_id].append(time.monotonic())

    def is_throttled(self, agent_id: str) -> bool:
        if agent_id not in self._throttle:
            return False
        limit = self._throttle[agent_id]
        now = time.monotonic()
        recent = [t for t in self._timestamps[agent_id] if now - t < 60.0]
        self._timestamps[agent_id] = recent
        return len(recent) >= limit

    @property
    def throttle_state(self) -> dict:
        return dict(self._throttle)
