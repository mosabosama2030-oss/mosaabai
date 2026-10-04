"""Strategy selector: pick reasoning strategies for a task.

Supports the Plan stage: the cognitive loop asks the selector which
reasoning strategies fit a task description, then plans with the
returned list (most relevant first).
"""

from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    """Reasoning strategies the cognitive loop can employ."""

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
    Strategy.DEDUCTIVE: ["prove", "therefore", "logically", "derive", "implies"],
    Strategy.INDUCTIVE: ["pattern", "trend", "generalize", "observe"],
    Strategy.ABDUCTIVE: ["diagnose", "why", "cause", "explain", "root"],
    Strategy.BAYESIAN: ["probability", "likely", "uncertain", "confidence"],
    Strategy.CAUSAL: ["cause", "effect", "impact", "influence"],
    Strategy.ANALOGICAL: ["similar", "like", "analogy", "compare"],
    Strategy.PLANNING: ["plan", "schedule", "steps", "roadmap", "strategy"],
    Strategy.SEARCH: ["find", "search", "explore", "lookup"],
    Strategy.HEURISTIC: ["quick", "approximate", "estimate", "best guess"],
    Strategy.EXPLORATORY: ["new", "novel", "unknown", "discover", "unfamiliar"],
    Strategy.MEMORY_BASED: ["before", "previously", "last time", "remember", "history"],
}

DEFAULT_STRATEGIES = [Strategy.DEDUCTIVE, Strategy.EXPLORATORY]


class StrategySelector:
    """Selects reasoning strategies by keyword matching against a task.

    Each strategy is scored by how many of its keywords appear in the
    task description (case-insensitive substring match). Matches are
    returned most relevant first; ties keep declaration order. Tasks
    with no matches fall back to DEFAULT_STRATEGIES.
    """

    def select(self, task_description: str, context: dict | None = None) -> list[Strategy]:
        """Return ordered strategies for a task, most relevant first.

        Empty or None tasks return the default pair. `context` is
        accepted for future memory-informed selection and does not
        affect matching yet.
        """
        if not task_description:
            return list(DEFAULT_STRATEGIES)

        text = task_description.lower()
        scored = [
            (sum(keyword in text for keyword in keywords), strategy)
            for strategy, keywords in STRATEGY_KEYWORDS.items()
        ]
        # Stable sort: ties keep STRATEGY_KEYWORDS declaration order.
        scored.sort(key=lambda pair: pair[0], reverse=True)
        matches = [strategy for count, strategy in scored if count > 0]
        return matches if matches else list(DEFAULT_STRATEGIES)
