from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EmailMessage

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = self._load_credentials()
        self.gmail_service = build("gmail", "v1", credentials=self.creds)
        self.calendar_service = build("calendar", "v3", credentials=self.creds)

    def _load_credentials(self) -> Credentials:
        creds = None
        if Path(self.token_file).exists():
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return creds

    def list_unread_messages(self, max_results: int = 10) -> List[Dict[str, Any]]:
        response = (
            self.gmail_service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )
        return response.get("messages", [])

    def get_message(self, message_id: str) -> EmailMessage:
        msg = (
            self.gmail_service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        headers = msg.get("payload", {}).get("headers", [])
        header_map = {h.get("name", "").lower(): h.get("value", "") for h in headers}

        body = self._extract_body(msg.get("payload", {}))
        attachments = self._extract_attachments(msg.get("payload", {}))

        return EmailMessage(
            id=msg.get("id", ""),
            thread_id=msg.get("threadId", ""),
            subject=header_map.get("subject", "(No Subject)"),
            sender=header_map.get("from", ""),
            snippet=msg.get("snippet", ""),
            body=body,
            received_at=header_map.get("date", ""),
            attachments=attachments,
            raw_payload=msg,
        )

    def create_reply_draft(self, to: str, subject: str, body: str, thread_id: str | None = None) -> Dict[str, Any]:
        mime = MIMEText(body)
        mime["to"] = to
        mime["subject"] = subject

        encoded_message = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        draft_body: Dict[str, Any] = {"message": {"raw": encoded_message}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        return self.gmail_service.users().drafts().create(userId="me", body=draft_body).execute()

    def archive_message(self, message_id: str) -> Dict[str, Any]:
        return (
            self.gmail_service.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["INBOX"], "addLabelIds": []},
            )
            .execute()
        )

    def save_attachments(self, message_id: str, output_dir: str) -> List[str]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        message = (
            self.gmail_service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        saved_files: List[str] = []

        def walk_parts(parts: List[Dict[str, Any]]) -> None:
            for part in parts:
                filename = part.get("filename")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")

                if filename and attachment_id:
                    attachment = (
                        self.gmail_service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message_id, id=attachment_id)
                        .execute()
                    )
                    data = attachment.get("data", "")
                    file_data = base64.urlsafe_b64decode(data.encode("UTF-8"))
                    path = os.path.join(output_dir, filename)
                    with open(path, "wb") as f:
                        f.write(file_data)
                    saved_files.append(path)

                if "parts" in part:
                    walk_parts(part["parts"])

        payload = message.get("payload", {})
        if "parts" in payload:
            walk_parts(payload["parts"])

        return saved_files

    def create_calendar_event(
        self,
        summary: str,
        start_iso: str,
        end_iso: str,
        description: str = "",
        location: str = "",
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        event = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
        }
        return self.calendar_service.events().insert(calendarId=calendar_id, body=event).execute()

    @staticmethod
    def _extract_body(payload: Dict[str, Any]) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data", "")
                if mime_type == "text/plain" and data:
                    return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8", errors="ignore")

            for part in payload["parts"]:
                if "parts" in part:
                    nested = GmailClient._extract_body(part)
                    if nested:
                        return nested

        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8", errors="ignore")

        return ""

    @staticmethod
    def _extract_attachments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        attachments: List[Dict[str, Any]] = []

        def walk(parts: List[Dict[str, Any]]) -> None:
            for part in parts:
                filename = part.get("filename", "")
                body = part.get("body", {})
                if filename and body.get("attachmentId"):
                    attachments.append(
                        {
                            "filename": filename,
                            "mimeType": part.get("mimeType", "application/octet-stream"),
                            "attachmentId": body.get("attachmentId"),
                            "size": body.get("size", 0),
                        }
                    )
                if "parts" in part:
                    walk(part["parts"])

        if "parts" in payload:
            walk(payload["parts"])

        return attachments
