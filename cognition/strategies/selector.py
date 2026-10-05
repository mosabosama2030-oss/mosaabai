"""Strategy selector: pick reasoning strategies for a task.

v0.2: keyword scoring + light weight boosts for multi-match strategies.
"""

from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    BAYESIAN = "bayesian"
    CAUSAL = "causal"
    ANALOGICAL = "analogical"
    PLANNING = "planning"
    SEARCH = "search"
    HEURISTIC = "heuristic"
    EXPLORATORY = "exploratory"
    MEMORY_BASED = "memory_based"


STRATEGY_KEYWORDS: dict[Strategy, list[str]] = {
    Strategy.DEDUCTIVE: ["prove", "therefore", "logically", "derive", "implies", "must"],
    Strategy.INDUCTIVE: ["pattern", "trend", "generalize", "observe", "usually"],
    Strategy.ABDUCTIVE: ["diagnose", "why", "cause", "explain", "root", "hypothesis"],
    Strategy.BAYESIAN: ["probability", "likely", "uncertain", "confidence", "odds"],
    Strategy.CAUSAL: ["cause", "effect", "impact", "influence", "leads to"],
    Strategy.ANALOGICAL: ["similar", "like", "analogy", "compare", "as if"],
    Strategy.PLANNING: ["plan", "schedule", "steps", "roadmap", "strategy", "how to"],
    Strategy.SEARCH: ["find", "search", "explore", "lookup", "locate"],
    Strategy.HEURISTIC: ["quick", "approximate", "estimate", "best guess", "rough"],
    Strategy.EXPLORATORY: ["new", "novel", "unknown", "discover", "unfamiliar"],
    Strategy.MEMORY_BASED: ["before", "previously", "last time", "remember", "history"],
}

DEFAULT_STRATEGIES = [Strategy.DEDUCTIVE, Strategy.EXPLORATORY]


class StrategySelector:
    """Selects reasoning strategies by keyword matching against a task."""

    def select(self, task_description: str, context: dict | None = None) -> list[Strategy]:
        if not task_description:
            return list(DEFAULT_STRATEGIES)

        text = task_description.lower()
        scored: list[tuple[int, Strategy]] = []
        for strategy, keywords in STRATEGY_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits:
                scored.append((hits, strategy))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        matches = [strategy for count, strategy in scored]
        return matches if matches else list(DEFAULT_STRATEGIES)
