from __future__ import annotations

from autotool_system.core.rule_engine import RuleEngine


def test_rule_engine_matches_and_priority() -> None:
    engine = RuleEngine()
    engine.add_rule(
        {
            "id": "r1",
            "condition": {"key": "status", "op": "eq", "value": "ok"},
            "priority": 0,
        }
    )
    engine.add_rule(
        {
            "id": "r2",
            "condition": {"any": [{"key": "level", "op": "gt", "value": 3}, {"key": "mode", "op": "eq", "value": "fast"}]},
            "priority": 5,
        }
    )

    matches = engine.evaluate({"status": "ok", "level": 2, "mode": "fast"})
    assert [rule["id"] for rule in matches] == ["r2", "r1"]


def test_rule_engine_remove() -> None:
    engine = RuleEngine()
    rule = engine.add_rule({"id": "r1", "condition": {"key": "a", "op": "eq", "value": 1}})
    assert rule.id == "r1"
    engine.remove_rule("r1")
    assert engine.evaluate({"a": 1}) == []
