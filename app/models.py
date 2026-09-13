from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class EmailType(str, Enum):
    MEETING = "meeting"
    QUERY = "query"
    SPAM = "spam"
    INFO = "info"
    ATTACHMENT = "attachment"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    DRAFT_REPLY = "draft_reply"
    ARCHIVE = "archive"
    SAVE_ATTACHMENTS = "save_attachments"
    SUMMARIZE = "summarize"
    NEEDS_REVIEW = "needs_review"


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    body: str
    received_at: str
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResult:
    email_type: EmailType
    confidence: float
    summary: str
    entities: Dict[str, Any] = field(default_factory=dict)
    suggested_action: str = ""


@dataclass
class Decision:
    action: ActionType
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
