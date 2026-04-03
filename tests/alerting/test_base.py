import dataclasses

from agentauth.alerting.base import AlertPayload

# A fully-typed default payload; tests can override fields via dataclasses.replace().
_DEFAULT_PAYLOAD = AlertPayload(
    agent_id=1,
    agent_name="Test Bot",
    threshold_pct=80,
    current_pct=85.0,
    current_spend=42.5,
    budget_usd=50.0,
    rule_id=1,
)


def _make_payload(**kwargs: object) -> AlertPayload:
    """Return a copy of the default ``AlertPayload`` with overridden fields."""
    return dataclasses.replace(_DEFAULT_PAYLOAD, **kwargs)  # type: ignore[arg-type]


def test_payload_subject():
    p = _make_payload()
    assert "Test Bot" in p.subject
    assert "80%" in p.subject
    assert "$42.50" in p.subject


def test_payload_body():
    p = _make_payload()
    assert "42.5" in p.body
    assert "$50.00" in p.body
    assert "threshold 80%" in p.body
