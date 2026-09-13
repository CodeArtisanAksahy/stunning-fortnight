from app.decision_engine import DecisionEngine
from app.models import ClassificationResult, EmailType


def test_low_confidence_goes_to_review() -> None:
    engine = DecisionEngine()
    cls = ClassificationResult(
        email_type=EmailType.QUERY,
        confidence=0.2,
        summary="",
    )
    decision = engine.decide(cls)
    assert decision.action.value == "needs_review"


def test_high_confidence_spam_archives() -> None:
    engine = DecisionEngine()
    cls = ClassificationResult(
        email_type=EmailType.SPAM,
        confidence=0.95,
        summary="",
    )
    decision = engine.decide(cls)
    assert decision.action.value == "archive"
