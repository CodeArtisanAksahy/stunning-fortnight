from __future__ import annotations

import os
from typing import Optional

from .models import ActionType, ClassificationResult, Decision, EmailMessage
from .gmail_client import GmailClient


class ActionExecutor:
    def __init__(self, gmail_client: GmailClient, calendar_id: Optional[str] = None) -> None:
        self.gmail_client = gmail_client
        self.calendar_id = calendar_id or os.getenv("CALENDAR_ID", "primary")

    def execute(
        self,
        email: EmailMessage,
        classification: ClassificationResult,
        decision: Decision,
        dry_run: bool = True,
        save_attachments_dir: str | None = None,
    ) -> str:
        if dry_run:
            return f"DRY_RUN: would execute {decision.action.value} for email {email.id}"

        if decision.action == ActionType.DRAFT_REPLY:
            reply = self._build_reply(email, classification)
            subject = self._reply_subject(email.subject)
            self.gmail_client.create_reply_draft(
                to=email.sender,
                subject=subject,
                body=reply,
                thread_id=email.thread_id,
            )
            return f"Created draft reply for {email.id}"

        if decision.action == ActionType.ARCHIVE:
            self.gmail_client.archive_message(email.id)
            return f"Archived email {email.id}"

        if decision.action == ActionType.SAVE_ATTACHMENTS:
            if not save_attachments_dir:
                return f"Skipped attachment save for {email.id}: no output directory provided"
            files = self.gmail_client.save_attachments(email.id, save_attachments_dir)
            return f"Saved {len(files)} attachment(s) for {email.id}"

        if decision.action == ActionType.CREATE_CALENDAR_EVENT:
            start_iso = str(decision.metadata.get("start_iso", ""))
            end_iso = str(decision.metadata.get("end_iso", ""))
            location = str(decision.metadata.get("location", ""))
            if not (start_iso and end_iso):
                return f"Skipped calendar event for {email.id}: missing start/end"

            event = self.gmail_client.create_calendar_event(
                summary=email.subject,
                start_iso=start_iso,
                end_iso=end_iso,
                description=classification.summary,
                location=location,
                calendar_id=self.calendar_id,
            )
            return f"Created calendar event {event.get('id', '(unknown)')} for {email.id}"

        if decision.action == ActionType.SUMMARIZE:
            return f"Summary for {email.id}: {classification.summary}"

        return f"Marked {email.id} for manual review"

    @staticmethod
    def _reply_subject(subject: str) -> str:
        if subject.lower().startswith("re:"):
            return subject
        return f"Re: {subject}"

    @staticmethod
    def _build_reply(email: EmailMessage, classification: ClassificationResult) -> str:
        return (
            "Hello,\n\n"
            "Thanks for your email. I reviewed your message and prepared this draft response:\n\n"
            f"{classification.summary}\n\n"
            "Please let me know if you'd like any further details.\n\n"
            "Best regards"
        )
