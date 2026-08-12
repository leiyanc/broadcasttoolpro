import html
import os
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin

from backend.services.email_outbox import (
    EmailOutboxStore,
    email_outbox_store,
)
from backend.services.email_suppression import (
    EmailSuppressionStore,
)


class EmailProvider(Protocol):
    def send(self, message: dict) -> str | None:
        """Deliver one outbox message and return the provider message ID."""


@dataclass(frozen=True)
class SesSettings:
    sender: str
    region: str
    reply_to: str | None = None

    @classmethod
    def from_environment(cls) -> "SesSettings":
        sender = os.getenv("BTP_EMAIL_FROM", "").strip()
        if not sender:
            raise RuntimeError(
                "BTP_EMAIL_FROM is required when Amazon SES is enabled."
            )
        return cls(
            sender=sender,
            region=(
                os.getenv("BTP_SES_REGION")
                or os.getenv("AWS_REGION")
                or "us-east-1"
            ).strip(),
            reply_to=os.getenv("BTP_EMAIL_REPLY_TO", "").strip() or None,
        )


class AmazonSesProvider:
    def __init__(self, settings: SesSettings | None = None):
        self.settings = settings or SesSettings.from_environment()
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "Install project dependencies before enabling Amazon SES."
            ) from exc
        self.client = boto3.client("sesv2", region_name=self.settings.region)

    @staticmethod
    def _html_body(message: dict) -> str:
        rendered_lines = []
        for line in message["body_text"].splitlines():
            if line.startswith("Open Billing: "):
                url = line.removeprefix("Open Billing: ").strip()
                safe_url = html.escape(url, quote=True)
                rendered_lines.append(
                    f'<a href="{safe_url}" style="display:inline-block;'
                    'padding:12px 18px;background:#1765ff;color:#ffffff;'
                    'text-decoration:none;border-radius:8px;font-weight:700">'
                    "Open Billing</a>"
                )
            else:
                safe_line = html.escape(line)
                safe_line = re.sub(
                    r"(https://[^\s<]+)",
                    r'<a href="\1">\1</a>',
                    safe_line,
                )
                rendered_lines.append(safe_line)
        body = "<br>".join(rendered_lines)
        application_url = os.getenv("BTP_APPLICATION_URL", "").strip()
        logo_url = (
            urljoin(
                f"{application_url.rstrip('/')}/",
                "/static/assets/broadcast-tool-pro-logo.png",
            )
            if application_url
            else ""
        )
        brand_header = (
            f'<img src="{html.escape(logo_url, quote=True)}" '
            'alt="Broadcast Tool Pro" width="240" '
            'style="display:block;width:240px;max-width:100%;height:auto;'
            'border:0;outline:none;text-decoration:none">'
            if logo_url
            else (
                '<div style="color:#1765ff;font-size:24px;font-weight:700">'
                "Broadcast Tool Pro</div>"
            )
        )
        return (
            '<div style="margin:0;padding:24px;background:#f4f7fb">'
            '<table role="presentation" width="100%" cellspacing="0" '
            'cellpadding="0" border="0" style="max-width:640px;margin:0 auto;'
            'background:#ffffff;border:1px solid #dbe4f0;border-radius:12px">'
            '<tr><td style="padding:28px 32px 20px">'
            f"{brand_header}</td></tr>"
            '<tr><td style="padding:0 32px 28px;font-family:Arial,sans-serif;'
            'color:#102842;font-size:15px;line-height:1.65">'
            f"<p style=\"margin:0\">{body}</p>"
            '<p style="margin:28px 0 0;padding-top:18px;border-top:1px solid '
            '#e5ebf3;color:#60728c;font-size:12px">'
            "All Your Broadcast Needs. One Place.</p>"
            "</td></tr></table></div>"
        )

    def send(self, message: dict) -> str | None:
        request = {
            "FromEmailAddress": self.settings.sender,
            "Destination": {
                "ToAddresses": [message["recipient_email"]],
            },
            "Content": {
                "Simple": {
                    "Subject": {
                        "Data": message["subject"],
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Text": {
                            "Data": message["body_text"],
                            "Charset": "UTF-8",
                        },
                        "Html": {
                            "Data": self._html_body(message),
                            "Charset": "UTF-8",
                        },
                    },
                }
            },
        }
        if self.settings.reply_to:
            request["ReplyToAddresses"] = [self.settings.reply_to]
        response = self.client.send_email(**request)
        return response.get("MessageId")


class EmailDeliveryService:
    def __init__(
        self,
        outbox: EmailOutboxStore = email_outbox_store,
        provider: EmailProvider | None = None,
        suppressions: EmailSuppressionStore | None = None,
    ):
        self.outbox = outbox
        self.provider = provider
        self.suppressions = suppressions or EmailSuppressionStore(
            outbox.database_path
        )
        self.suppressions.initialize()

    @staticmethod
    def is_enabled() -> bool:
        return os.getenv("BTP_EMAIL_PROVIDER", "").strip().lower() == "ses"

    def _provider(self) -> EmailProvider:
        if self.provider is not None:
            return self.provider
        self.provider = AmazonSesProvider()
        return self.provider

    def deliver_due(self, limit: int = 25) -> dict:
        if self.provider is None and not self.is_enabled():
            return {"enabled": False, "claimed": 0, "sent": 0, "failed": 0}
        messages = self.outbox.claim_pending(limit)
        sent = 0
        failed = 0
        provider = self._provider()
        for message in messages:
            try:
                provider_message_id = provider.send(message)
            except Exception as exc:
                self.outbox.mark_delivery_failure(message["id"], str(exc))
                failed += 1
            else:
                self.outbox.mark_sent(
                    message["id"],
                    provider_message_id,
                )
                self.suppressions.record_event(
                    event_type="send",
                    recipient_email=message["recipient_email"],
                    provider="amazon_ses",
                    provider_message_id=provider_message_id,
                    details={
                        "template_code": message["template_code"],
                        "outbox_message_id": message["id"],
                    },
                )
                sent += 1
        return {
            "enabled": True,
            "claimed": len(messages),
            "sent": sent,
            "failed": failed,
        }


email_delivery_service = EmailDeliveryService()
