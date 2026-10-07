"""SMTP Email Provider implementation and interface."""

from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.core.config import settings
from app.core.logging import logger


class EmailProvider(ABC):
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Sends an email message."""
        pass


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider sending via Mailpit or configured SMTP server."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host or "mailpit"
        self.port = port or 1025
        self.user = user or ""
        self.password = password or ""
        self.from_email = from_email or "no-reply@agriscope.local"
        self.use_tls = use_tls or False

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        plain_part = MIMEText(text_content or html_content, "plain")
        html_part = MIMEText(html_content, "html")
        msg.attach(plain_part)
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info(f"Email sent successfully to {to_email} with subject '{subject}'")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via SMTP: {e}")
            return False


class MockEmailProvider(EmailProvider):
    """In-memory mock email provider for testing and offline execution."""

    sent_emails: List[dict] = []

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        record = {
            "to": to_email,
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
        self.sent_emails.append(record)
        logger.info(f"[MockEmailProvider] Stored email to {to_email} ('{subject}')")
        return True

    @classmethod
    def clear(cls) -> None:
        cls.sent_emails.clear()


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER.lower() == "smtp":
        return SMTPEmailProvider()
    return MockEmailProvider()
