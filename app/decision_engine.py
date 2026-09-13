from __future__ import annotations

from .models import ActionType, ClassificationResult, Decision, EmailType


class DecisionEngine:
    def __init__(self) -> None:
        self.thresholds = {
            EmailType.MEETING: 0.85,
            EmailType.QUERY: 0.75,
            EmailType.SPAM: 0.9,
            EmailType.ATTACHMENT: 0.75,
            EmailType.INFO: 0.7,
            EmailType.UNKNOWN: 0.95,
        }

    def decide(self, result: ClassificationResult) -> Decision:
        min_conf = self.thresholds.get(result.email_type, 0.95)
        if result.confidence < min_conf:
            return Decision(
                action=ActionType.NEEDS_REVIEW,
                reason=f"Confidence {result.confidence:.2f} below threshold {min_conf:.2f}",
            )

        if result.email_type == EmailType.MEETING:
            if result.entities.get("start_iso") and result.entities.get("end_iso"):
                return Decision(
                    action=ActionType.CREATE_CALENDAR_EVENT,
                    reason="Meeting email with time entities extracted.",
                    metadata={
                        "start_iso": result.entities.get("start_iso"),
                        "end_iso": result.entities.get("end_iso"),
                        "location": result.entities.get("location", ""),
                    },
                )
            return Decision(
                action=ActionType.NEEDS_REVIEW,
                reason="Meeting detected but no reliable datetime entities.",
            )

        if result.email_type == EmailType.QUERY:
            return Decision(action=ActionType.DRAFT_REPLY, reason="User query needs response draft.")

        if result.email_type == EmailType.SPAM:
            return Decision(action=ActionType.ARCHIVE, reason="Likely spam with high confidence.")

        if result.email_type == EmailType.ATTACHMENT:
            return Decision(action=ActionType.SAVE_ATTACHMENTS, reason="Attachment-centric email.")

        if result.email_type == EmailType.INFO:
            return Decision(action=ActionType.SUMMARIZE, reason="Informational email summary.")

        return Decision(action=ActionType.NEEDS_REVIEW, reason="No safe deterministic action.")
