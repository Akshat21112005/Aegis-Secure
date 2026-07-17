"""Shared email text formatting for semantic training and inference."""


def format_email_text(subject: str, body: str) -> str:
    subject = (subject or "").strip()
    body = (body or "").strip()
    return f"[SUBJECT]\n{subject}\n\n[BODY]\n{body}"
