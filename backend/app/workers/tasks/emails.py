"""Email delivery tasks and HTML/Text templates."""

from __future__ import annotations

from app.core.logging import logger
from app.providers.email.smtp import get_email_provider
from app.workers.celery_app import celery_app


def render_verification_email(name: str, verify_url: str) -> tuple[str, str]:
    """Generates HTML and plain text for email verification."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <h2 style="color: #16a34a; margin-top: 0;">Welcome to AgriScope!</h2>
            <p>Hello {name},</p>
            <p>Thank you for signing up. Please verify your email address to activate your AgriScope account:</p>
            <p style="text-align: center; margin: 24px 0;">
                <a href="{verify_url}" style="background-color: #16a34a; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                    Verify My Email
                </a>
            </p>
            <p style="font-size: 13px; color: #64748b;">This verification link will expire in 24 hours. If you did not create this account, please disregard this email.</p>
        </div>
    </body>
    </html>
    """
    text = f"""Welcome to AgriScope, {name}!
    
Please verify your email address using the following link:
{verify_url}

This link expires in 24 hours.
"""
    return html.strip(), text.strip()


def render_password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    """Generates HTML and plain text for password reset."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <h2 style="color: #0f172a; margin-top: 0;">Reset Your Password</h2>
            <p>Hello {name},</p>
            <p>We received a request to reset your AgriScope password. Click the button below to choose a new password:</p>
            <p style="text-align: center; margin: 24px 0;">
                <a href="{reset_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="font-size: 13px; color: #64748b;">This link is valid for 1 hour and can only be used once. If you did not request this, your account remains secure and you can ignore this email.</p>
        </div>
    </body>
    </html>
    """
    text = f"""Hello {name},

We received a request to reset your AgriScope password.
Visit this link to reset your password:
{reset_url}

This link expires in 1 hour and can only be used once.
"""
    return html.strip(), text.strip()


@celery_app.task(name="app.workers.tasks.emails.send_verification_email")
def send_verification_email_task(to_email: str, name: str, verify_url: str) -> bool:
    html, text = render_verification_email(name, verify_url)
    provider = get_email_provider()
    logger.info(f"Triggering email verification task for {to_email}")
    return provider.send_email(
        to_email=to_email,
        subject="Verify your AgriScope Account",
        html_content=html,
        text_content=text,
    )


@celery_app.task(name="app.workers.tasks.emails.send_password_reset_email")
def send_password_reset_email_task(to_email: str, name: str, reset_url: str) -> bool:
    html, text = render_password_reset_email(name, reset_url)
    provider = get_email_provider()
    logger.info(f"Triggering password reset email task for {to_email}")
    return provider.send_email(
        to_email=to_email,
        subject="Reset your AgriScope Password",
        html_content=html,
        text_content=text,
    )
