"""Tests for PricingTable cost calculations."""

import pytest
from burnrate.pricing import PricingTable


@pytest.fixture
def table():
    return PricingTable()


def test_known_model_gpt4o(table):
    cost = table.cost("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["input"] == pytest.approx(2.50)
    assert cost["output"] == pytest.approx(10.00)
    assert cost["total"] == pytest.approx(12.50)
    assert not cost["unknown_model"]


def test_known_model_claude_sonnet(table):
    cost = table.cost(
        "claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=500_000,
        cache_creation_tokens=200_000,
        cache_read_tokens=800_000,
    )
    assert cost["input"] == pytest.approx(3.00)
    assert cost["output"] == pytest.approx(7.50)
    assert cost["cache_creation"] == pytest.approx(0.75)
    assert cost["cache_read"] == pytest.approx(0.24)
    assert cost["total"] == pytest.approx(11.49)
    assert not cost["unknown_model"]


def test_reasoning_tokens(table):
    cost = table.cost("o3", input_tokens=100_000, output_tokens=50_000, reasoning_tokens=200_000)
    assert cost["reasoning"] == pytest.approx(2.00)


def test_unknown_model_returns_zeros(table):
    cost = table.cost("gpt-99-ultra-turbo", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["total"] == 0.0
    assert cost["unknown_model"] is True


def test_fuzzy_model_match(table):
    # versioned alias should match base model
    cost = table.cost("gpt-4o-2024-08-06", input_tokens=1_000_000)
    assert cost["input"] == pytest.approx(2.50)
    assert not cost["unknown_model"]


def test_runtime_registration(table):
    table.register("my-custom-model", {"input": 5.0, "output": 20.0,
                                        "cache_creation": 0.0, "cache_read": 0.0, "reasoning": 0.0})
    cost = table.cost("my-custom-model", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["total"] == pytest.approx(25.0)


def test_zero_tokens_returns_zeros(table):
    cost = table.cost("gpt-4o")
    assert cost["total"] == 0.0


def test_cache_hit_cheaper_than_input(table):
    full = table.cost("gpt-4o", input_tokens=1_000_000)
    cached = table.cost("gpt-4o", cache_read_tokens=1_000_000)
    assert cached["cache_read"] < full["input"]
