from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI

from .models import ClassificationResult, EmailMessage, EmailType
from .prompts import CLASSIFIER_SYSTEM_PROMPT


class EmailClassifier:
    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def classify(self, email: EmailMessage) -> ClassificationResult:
        if not self.client:
            return self._heuristic_classify(email)

        payload = {
            "subject": email.subject,
            "from": email.sender,
            "snippet": email.snippet,
            "body": email.body[:6000],
            "attachments": [a.get("filename", "") for a in email.attachments],
        }

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )

        content = response.choices[0].message.content or "{}"
        parsed = self._safe_json_load(content)
        return self._to_result(parsed)

    def _heuristic_classify(self, email: EmailMessage) -> ClassificationResult:
        text = f"{email.subject} {email.snippet} {email.body}".lower()

        if any(k in text for k in ["unsubscribe", "offer", "discount", "buy now", "limited time"]):
            return ClassificationResult(
                email_type=EmailType.SPAM,
                confidence=0.92,
                summary="Likely promotional/spam email.",
                suggested_action="archive",
            )

        if any(k in text for k in ["meeting", "calendar", "schedule", "invite", "zoom", "teams"]):
            return ClassificationResult(
                email_type=EmailType.MEETING,
                confidence=0.78,
                summary="Email appears to be meeting-related.",
                suggested_action="create_calendar_event",
            )

        if email.attachments:
            return ClassificationResult(
                email_type=EmailType.ATTACHMENT,
                confidence=0.8,
                summary="Email includes attachments that may need saving.",
                entities={"attachments": [a.get("filename", "") for a in email.attachments]},
                suggested_action="save_attachments",
            )

        if "?" in text or any(k in text for k in ["can you", "could you", "please clarify", "what is"]):
            return ClassificationResult(
                email_type=EmailType.QUERY,
                confidence=0.76,
                summary="Email contains a question.",
                suggested_action="draft_reply",
            )

        return ClassificationResult(
            email_type=EmailType.INFO,
            confidence=0.65,
            summary="Informational email.",
            suggested_action="summarize",
        )

    @staticmethod
    def _safe_json_load(content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _to_result(payload: Dict[str, Any]) -> ClassificationResult:
        raw_type = str(payload.get("type", "unknown")).lower()
        try:
            email_type = EmailType(raw_type)
        except ValueError:
            email_type = EmailType.UNKNOWN

        confidence = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(confidence, 1.0))

        summary = str(payload.get("summary", "No summary."))
        entities = payload.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        suggested_action = str(payload.get("suggested_action", "needs_review"))

        return ClassificationResult(
            email_type=email_type,
            confidence=confidence,
            summary=summary,
            entities=entities,
            suggested_action=suggested_action,
        )
