from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .actions import ActionExecutor
from .classifier import EmailClassifier
from .decision_engine import DecisionEngine
from .gmail_client import GmailClient


def configure_logging() -> None:
    Path("data").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("data/audit.log"),
            logging.StreamHandler(),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Email Agent")
    parser.add_argument("--max-emails", type=int, default=10, help="Max unread emails to process")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute actions (default is dry-run)",
    )
    parser.add_argument(
        "--save-attachments-dir",
        type=str,
        default="",
        help="Directory to save email attachments",
    )
    return parser.parse_args()


def run() -> None:
    load_dotenv()
    configure_logging()
    args = parse_args()

    credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    gmail_client = GmailClient(credentials_file=credentials_file, token_file=token_file)
    classifier = EmailClassifier()
    decision_engine = DecisionEngine()
    executor = ActionExecutor(gmail_client=gmail_client)

    unread = gmail_client.list_unread_messages(max_results=args.max_emails)
    if not unread:
        logging.info("No unread emails found.")
        return

    for item in unread:
        message_id = item.get("id")
        if not message_id:
            continue

        email = gmail_client.get_message(message_id)
        classification = classifier.classify(email)
        decision = decision_engine.decide(classification)

        result = executor.execute(
            email=email,
            classification=classification,
            decision=decision,
            dry_run=not args.execute,
            save_attachments_dir=args.save_attachments_dir or None,
        )

        logging.info(
            "email_id=%s type=%s confidence=%.2f action=%s reason=%s result=%s",
            email.id,
            classification.email_type.value,
            classification.confidence,
            decision.action.value,
            decision.reason,
            result,
        )


if __name__ == "__main__":
    run()
