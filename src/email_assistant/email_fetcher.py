from typing import Sequence

SAMPLE_EMAILS: list[dict[str, str]] = [
    {
        "sender": "sarah.chen@example.com",
        "subject": "Meeting Request — Project Q3 Review",
        "body": (
            "Hi team,\n\n"
            "I'd like to schedule a Q3 project review meeting next week. "
            "Please let me know your availability for Tuesday or Wednesday "
            "afternoon.\n\n"
            "Best regards,\n"
            "Sarah Chen"
        ),
        "timestamp": "2026-07-28T14:30:00Z",
    },
    {
        "sender": "notifications@secureplatform.com",
        "subject": "Action Required: Verify Your Account Email Address",
        "body": (
            "Hello,\n\n"
            "We recently detected a login attempt from a new device. To ensure "
            "the security of your account, please verify your email address by "
            "clicking the link below.\n\n"
            "This link will expire in 24 hours. If you did not attempt to log "
            "in, please ignore this email or contact our support team "
            "immediately.\n\n"
            "Thank you for keeping your account secure.\n\n"
            "Best regards,\n"
            "Security Team"
        ),
        "timestamp": "2026-07-29T09:15:43Z",
    },
    {
        "sender": "newsletter@dealsdaily.com",
        "subject": "🔥 70% OFF Everything — Limited Time!",
        "body": (
            "Don't miss out on our biggest sale of the year! "
            "70% off storewide, plus free shipping on orders over $50. "
            "Shop now at dealsdaily.com/sale."
        ),
        "timestamp": "2026-07-30T06:00:00Z",
    },
]


def format_email(email: dict[str, str]) -> str:
    """Render a structured email dict into a plain-text block for the LLM."""
    return (
        f"From: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Date: {email['timestamp']}\n"
        f"\n"
        f"{email['body']}"
    )


def fetch_emails() -> Sequence[dict[str, str]]:
    """Fetch unread emails from the inbox.

    Currently returns static sample data. Will be replaced with IMAP/Gmail API
    integration in a future phase.
    """
    return SAMPLE_EMAILS
