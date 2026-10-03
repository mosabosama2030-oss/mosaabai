"""Tests for the strategy selector."""

from __future__ import annotations

import pytest

from cognition.strategies.selector import STRATEGY_KEYWORDS, Strategy, StrategySelector


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ("prove this theorem", Strategy.DEDUCTIVE),
        ("observe the trend", Strategy.INDUCTIVE),
        ("diagnose the issue", Strategy.ABDUCTIVE),
        ("what is the probability", Strategy.BAYESIAN),
        ("the effect of rain", Strategy.CAUSAL),
        ("an analogy to birds", Strategy.ANALOGICAL),
        ("schedule the steps", Strategy.PLANNING),
        ("lookup the value", Strategy.SEARCH),
        ("quick estimate of the load", Strategy.HEURISTIC),
        ("discover novel ideas", Strategy.EXPLORATORY),
        ("what did we do last time", Strategy.MEMORY_BASED),
    ],
)
def test_each_category_selects_expected_strategy(task: str, expected: Strategy) -> None:
    result = StrategySelector().select(task)
    assert result[0] == expected


def test_default_when_no_keywords_match() -> None:
    result = StrategySelector().select("zzz qqq wobble")
    assert result == [Strategy.DEDUCTIVE, Strategy.EXPLORATORY]


def test_default_when_empty_string() -> None:
    result = StrategySelector().select("")
    assert result == [Strategy.DEDUCTIVE, Strategy.EXPLORATORY]


def test_default_when_none() -> None:
    result = StrategySelector().select(None)
    assert result == [Strategy.DEDUCTIVE, Strategy.EXPLORATORY]


def test_more_keyword_hits_rank_higher() -> None:
    # INDUCTIVE matches "pattern" and "trend" (2); SEARCH matches "find" (1).
    result = StrategySelector().select("find the pattern in the trend")
    assert result == [Strategy.INDUCTIVE, Strategy.SEARCH]


def test_multiple_categories_in_same_task() -> None:
    # ABDUCTIVE: diagnose + cause + root (3); PLANNING: plan + roadmap (2);
    # CAUSAL: cause (1).
    result = StrategySelector().select("diagnose the root cause and plan the roadmap")
    assert result == [Strategy.ABDUCTIVE, Strategy.PLANNING, Strategy.CAUSAL]


def test_returns_only_matching_strategies() -> None:
    result = StrategySelector().select("prove the theorem")
    assert result == [Strategy.DEDUCTIVE]


def test_case_insensitive_matching() -> None:
    selector = StrategySelector()
    assert selector.select("PROVE THAT X IMPLIES Y")[0] == Strategy.DEDUCTIVE
    assert selector.select("What Happened Last Time")[0] == Strategy.MEMORY_BASED


def test_every_strategy_has_keywords() -> None:
    assert set(STRATEGY_KEYWORDS) == set(Strategy)
    assert all(STRATEGY_KEYWORDS.values())


def test_context_argument_is_accepted() -> None:
    result = StrategySelector().select("prove the theorem", context={"memory": "prior run"})
    assert result == [Strategy.DEDUCTIVE]
