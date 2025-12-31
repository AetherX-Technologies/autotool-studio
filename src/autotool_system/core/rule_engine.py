from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


Condition = Mapping[str, Any] | Iterable[Any] | Callable[[Mapping[str, Any]], bool]


@dataclass
class Rule:
    id: str
    condition: Condition
    strategy: str = "all"
    priority: int = 0
    enabled: bool = True
    meta: dict[str, Any] = field(default_factory=dict)

    def matches(self, context: Mapping[str, Any]) -> bool:
        if not self.enabled:
            return False
        return _evaluate_condition(self.condition, context, self.strategy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "condition": self.condition,
            "strategy": self.strategy,
            "priority": self.priority,
            "enabled": self.enabled,
            "meta": dict(self.meta),
        }


class RuleEngine:
    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def add_rule(self, rule: Rule | Mapping[str, Any]) -> Rule:
        if isinstance(rule, Rule):
            self._rules.append(rule)
            return rule
        if not isinstance(rule, Mapping):
            raise ValueError("Rule must be a mapping or Rule instance")
        rule_id = str(rule.get("id") or uuid4())
        condition = rule.get("condition") or rule.get("conditions")
        if condition is None:
            raise ValueError("Rule requires condition or conditions")
        strategy = str(rule.get("strategy", "all")).lower()
        priority = int(rule.get("priority", 0))
        enabled = bool(rule.get("enabled", True))
        meta = rule.get("meta", {})
        new_rule = Rule(
            id=rule_id,
            condition=condition,
            strategy=strategy,
            priority=priority,
            enabled=enabled,
            meta=dict(meta) if isinstance(meta, Mapping) else {},
        )
        self._rules.append(new_rule)
        return new_rule

    def remove_rule(self, rule_id: str) -> None:
        self._rules = [rule for rule in self._rules if rule.id != rule_id]

    def evaluate(self, context: Mapping[str, Any]) -> list[dict[str, Any]]:
        matches = [rule for rule in self._rules if rule.matches(context)]
        matches.sort(key=lambda item: (-item.priority, item.id))
        return [rule.to_dict() for rule in matches]

    @property
    def rules(self) -> list[dict[str, Any]]:
        return [rule.to_dict() for rule in self._rules]


def _evaluate_condition(condition: Condition, context: Mapping[str, Any], strategy: str) -> bool:
    if callable(condition):
        return bool(condition(context))
    if isinstance(condition, Mapping):
        if "any" in condition:
            return any(_evaluate_condition(item, context, "all") for item in condition["any"])
        if "all" in condition:
            return all(_evaluate_condition(item, context, "all") for item in condition["all"])
        if "key" in condition:
            return _evaluate_single(condition, context)
        return all(context.get(key) == value for key, value in condition.items())
    if isinstance(condition, Iterable):
        items = list(condition)
        if strategy == "any":
            return any(_evaluate_condition(item, context, "all") for item in items)
        return all(_evaluate_condition(item, context, "all") for item in items)
    return False


def _evaluate_single(condition: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    key = condition.get("key")
    op = str(condition.get("op", "eq")).lower()
    expected = condition.get("value")
    actual = context.get(key)

    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual is not None and actual > expected
    if op == "gte":
        return actual is not None and actual >= expected
    if op == "lt":
        return actual is not None and actual < expected
    if op == "lte":
        return actual is not None and actual <= expected
    if op == "contains":
        if actual is None:
            return False
        return expected in actual
    if op == "in":
        if expected is None:
            return False
        return actual in expected
    if op == "not_in":
        if expected is None:
            return False
        return actual not in expected
    return False
