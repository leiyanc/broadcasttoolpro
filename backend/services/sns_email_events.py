"""Authenticate Amazon SNS messages and process Amazon SES email events."""

import base64
import json
import os
import re
from collections.abc import Callable
from urllib.parse import urlparse
from urllib.request import urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from backend.services.email_suppression import (
    EmailSuppressionStore,
    email_suppression_store,
)


SNS_HOST_PATTERN = re.compile(
    r"^sns\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?$"
)
SNS_MESSAGE_FIELDS = {
    "Notification": (
        "Message",
        "MessageId",
        "Subject",
        "Timestamp",
        "TopicArn",
        "Type",
    ),
    "SubscriptionConfirmation": (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
    "UnsubscribeConfirmation": (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
}


def _trusted_sns_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and SNS_HOST_PATTERN.fullmatch(parsed.hostname) is not None
        and parsed.username is None
        and parsed.password is None
        and parsed.port in {None, 443}
    )


def _download(url: str) -> bytes:
    if not _trusted_sns_url(url):
        raise ValueError("Amazon SNS URL is not trusted.")
    with urlopen(url, timeout=5) as response:
        return response.read()


class SnsMessageVerifier:
    def __init__(
        self,
        *,
        topic_arn: str | None = None,
        certificate_fetcher: Callable[[str], bytes] = _download,
    ):
        self.topic_arn = (
            topic_arn or os.getenv("BTP_SES_SNS_TOPIC_ARN", "")
        ).strip()
        self.certificate_fetcher = certificate_fetcher

    @staticmethod
    def canonical_message(message: dict) -> bytes:
        message_type = message.get("Type")
        fields = SNS_MESSAGE_FIELDS.get(message_type)
        if fields is None:
            raise ValueError("Unsupported Amazon SNS message type.")
        parts: list[str] = []
        for field in fields:
            if field == "Subject" and field not in message:
                continue
            if field not in message:
                raise ValueError(f"Amazon SNS field is missing: {field}.")
            parts.extend((field, str(message[field])))
        return ("\n".join(parts) + "\n").encode("utf-8")

    def verify(self, message: dict) -> None:
        if not self.topic_arn:
            raise RuntimeError(
                "BTP_SES_SNS_TOPIC_ARN must be configured before accepting "
                "Amazon SNS events."
            )
        if message.get("TopicArn") != self.topic_arn:
            raise ValueError("Amazon SNS topic is not authorized.")
        certificate_url = str(message.get("SigningCertURL", ""))
        if not _trusted_sns_url(certificate_url):
            raise ValueError("Amazon SNS signing certificate URL is invalid.")
        signature_version = str(message.get("SignatureVersion", ""))
        algorithm = {
            "1": hashes.SHA1(),
            "2": hashes.SHA256(),
        }.get(signature_version)
        if algorithm is None:
            raise ValueError("Unsupported Amazon SNS signature version.")
        try:
            signature = base64.b64decode(
                str(message["Signature"]),
                validate=True,
            )
            certificate = x509.load_pem_x509_certificate(
                self.certificate_fetcher(certificate_url)
            )
            certificate.public_key().verify(
                signature,
                self.canonical_message(message),
                padding.PKCS1v15(),
                algorithm,
            )
        except KeyError as exc:
            raise ValueError("Amazon SNS signature is missing.") from exc
        except Exception as exc:
            raise ValueError(
                "Amazon SNS signature verification failed."
            ) from exc


class SesSnsEventProcessor:
    def __init__(
        self,
        suppressions: EmailSuppressionStore = email_suppression_store,
    ):
        self.suppressions = suppressions

    @staticmethod
    def _event_type(payload: dict) -> str:
        return str(
            payload.get("eventType")
            or payload.get("notificationType")
            or ""
        ).lower()

    @staticmethod
    def _recipients(payload: dict, event_type: str) -> list[str]:
        event_recipients = {
            "bounce": (
                payload.get("bounce", {}).get("bouncedRecipients", [])
            ),
            "complaint": (
                payload.get("complaint", {}).get(
                    "complainedRecipients",
                    [],
                )
            ),
        }
        if event_type in event_recipients:
            return [
                item["emailAddress"]
                for item in event_recipients[event_type]
                if item.get("emailAddress")
            ]
        delivery = payload.get("delivery", {})
        if event_type == "delivery" and delivery.get("recipients"):
            return list(delivery["recipients"])
        return list(payload.get("mail", {}).get("destination", []))

    def process(self, sns_message: dict) -> dict:
        payload = json.loads(sns_message["Message"])
        event_type = self._event_type(payload)
        mapping = {
            "send": "send",
            "delivery": "delivery",
            "complaint": "complaint",
            "reject": "reject",
        }
        if event_type == "bounce":
            bounce_type = str(
                payload.get("bounce", {}).get("bounceType", "")
            ).lower()
            internal_type = (
                "permanent_bounce"
                if bounce_type == "permanent"
                else "temporary_bounce"
            )
        else:
            internal_type = mapping.get(event_type)
        if internal_type is None:
            return {
                "accepted": True,
                "recorded": 0,
                "ignored_event_type": event_type or "unknown",
            }
        recipients = self._recipients(payload, event_type)
        provider_message_id = payload.get("mail", {}).get("messageId")
        details = {
            "sns_message_id": sns_message.get("MessageId"),
            "ses_event_type": event_type,
        }
        if event_type == "bounce":
            details.update(payload.get("bounce", {}))
        elif event_type == "complaint":
            details.update(payload.get("complaint", {}))
        elif event_type == "reject":
            details.update(payload.get("reject", {}))
        for recipient in dict.fromkeys(recipients):
            self.suppressions.record_event(
                event_type=internal_type,
                recipient_email=recipient,
                provider="amazon_ses",
                provider_message_id=provider_message_id,
                details=details,
            )
        return {
            "accepted": True,
            "recorded": len(set(recipients)),
            "event_type": internal_type,
        }


def confirm_sns_subscription(subscribe_url: str) -> None:
    _download(subscribe_url)
