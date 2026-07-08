"""
Pricing table for LLM models.

Prices are per 1M tokens in USD. Structure per model:
  input, output, cache_creation, cache_read, reasoning
  (cache_creation = Anthropic prompt-cache write; cache_read = cache hit read)
  (reasoning = OpenAI o-series chain-of-thought tokens)

The table is loaded from BURNRATE_PRICING_FILE env var if set, otherwise from
the bundled default. You can override specific models at runtime.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_TABLE: dict[str, Any] = {
    # ── OpenAI ───────────────────────────────────────────────────────────────
    "gpt-4o": {
        "input": 2.50, "output": 10.00,
        "cache_read": 1.25, "cache_creation": 0.0, "reasoning": 0.0,
    },
    "gpt-4o-mini": {
        "input": 0.15, "output": 0.60,
        "cache_read": 0.075, "cache_creation": 0.0, "reasoning": 0.0,
    },
    "gpt-4o-mini-2024-07-18": {
        "input": 0.15, "output": 0.60,
        "cache_read": 0.075, "cache_creation": 0.0, "reasoning": 0.0,
    },
    "gpt-4-turbo": {
        "input": 10.00, "output": 30.00,
        "cache_read": 0.0, "cache_creation": 0.0, "reasoning": 0.0,
    },
    "o3": {
        "input": 10.00, "output": 40.00,
        "cache_read": 2.50, "cache_creation": 0.0, "reasoning": 10.00,
    },
    "o3-mini": {
        "input": 1.10, "output": 4.40,
        "cache_read": 0.55, "cache_creation": 0.0, "reasoning": 1.10,
    },
    "o4-mini": {
        "input": 1.10, "output": 4.40,
        "cache_read": 0.275, "cache_creation": 0.0, "reasoning": 1.10,
    },
    # ── Anthropic ────────────────────────────────────────────────────────────
    "claude-sonnet-4-6": {
        "input": 3.00, "output": 15.00,
        "cache_creation": 3.75, "cache_read": 0.30, "reasoning": 0.0,
    },
    "claude-opus-4-8": {
        "input": 15.00, "output": 75.00,
        "cache_creation": 18.75, "cache_read": 1.50, "reasoning": 0.0,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80, "output": 4.00,
        "cache_creation": 1.00, "cache_read": 0.08, "reasoning": 0.0,
    },
    "claude-fable-5": {
        "input": 3.00, "output": 15.00,
        "cache_creation": 3.75, "cache_read": 0.30, "reasoning": 0.0,
    },
    # Legacy aliases
    "claude-3-5-sonnet-20241022": {
        "input": 3.00, "output": 15.00,
        "cache_creation": 3.75, "cache_read": 0.30, "reasoning": 0.0,
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.80, "output": 4.00,
        "cache_creation": 1.00, "cache_read": 0.08, "reasoning": 0.0,
    },
    # ── Google ───────────────────────────────────────────────────────────────
    "gemini-2.5-pro": {
        "input": 1.25, "output": 10.00,
        "cache_creation": 0.0, "cache_read": 0.31, "reasoning": 0.0,
    },
    "gemini-2.5-flash": {
        "input": 0.30, "output": 2.50,
        "cache_creation": 0.0, "cache_read": 0.075, "reasoning": 0.0,
    },
    "gemini-2.0-flash": {
        "input": 0.10, "output": 0.40,
        "cache_creation": 0.0, "cache_read": 0.025, "reasoning": 0.0,
    },
    # ── Open / self-hosted (zero cost, still useful for token tracking) ──────
    "llama-3.3-70b": {
        "input": 0.0, "output": 0.0,
        "cache_creation": 0.0, "cache_read": 0.0, "reasoning": 0.0,
    },
    "mistral-large": {
        "input": 2.00, "output": 6.00,
        "cache_creation": 0.0, "cache_read": 0.0, "reasoning": 0.0,
    },
}

_PER_MILLION = 1_000_000.0


class PricingTable:
    """Immutable pricing lookup with optional file-based override."""

    def __init__(self, extra: dict[str, Any] | None = None) -> None:
        self._table: dict[str, Any] = {**_DEFAULT_TABLE}
        env_file = os.getenv("BURNRATE_PRICING_FILE")
        if env_file:
            self._table.update(json.loads(Path(env_file).read_text()))
        if extra:
            self._table.update(extra)

    def get(self, model: str) -> dict[str, float] | None:
        """Return pricing entry or None if model unknown."""
        key = model.lower().strip()
        if key in self._table:
            return self._table[key]
        # Fuzzy prefix match (e.g. "gpt-4o-2024-11-20" → "gpt-4o")
        for k, v in self._table.items():
            if key.startswith(k) or k.startswith(key.split("-202")[0]):
                return v
        return None

    def cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> dict[str, float]:
        """
        Calculate costs in USD. Returns a dict with keys:
        input, output, cache_creation, cache_read, reasoning, total.
        Returns all-zero dict if model is unknown (with unknown=True flag).
        """
        prices = self.get(model)
        if prices is None:
            return {
                "input": 0.0, "output": 0.0, "cache_creation": 0.0,
                "cache_read": 0.0, "reasoning": 0.0, "total": 0.0,
                "unknown_model": True,
            }

        c_input = (input_tokens / _PER_MILLION) * prices.get("input", 0.0)
        c_output = (output_tokens / _PER_MILLION) * prices.get("output", 0.0)
        c_cc = (cache_creation_tokens / _PER_MILLION) * prices.get("cache_creation", 0.0)
        c_cr = (cache_read_tokens / _PER_MILLION) * prices.get("cache_read", 0.0)
        c_reason = (reasoning_tokens / _PER_MILLION) * prices.get("reasoning", 0.0)

        return {
            "input": c_input,
            "output": c_output,
            "cache_creation": c_cc,
            "cache_read": c_cr,
            "reasoning": c_reason,
            "total": c_input + c_output + c_cc + c_cr + c_reason,
            "unknown_model": False,
        }

    def register(self, model: str, prices: dict[str, float]) -> None:
        """Register or update a model's pricing at runtime."""
        self._table[model.lower()] = prices
