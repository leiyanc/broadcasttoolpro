import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from backend.services.email_outbox import EmailOutboxStore
from backend.services.email_suppression import EmailSuppressionStore
from backend.services.sns_email_events import (
    SesSnsEventProcessor,
    SnsMessageVerifier,
)
from backend.services.tenant_store import TenantStore


TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:btp-email-events"
CERTIFICATE_URL = (
    "https://sns.us-east-1.amazonaws.com/"
    "SimpleNotificationService-test.pem"
)


def _certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Amazon SNS Test")]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(
            datetime.now(timezone.utc).replace(year=2030)
        )
        .sign(key, hashes.SHA256())
    )
    return key, certificate.public_bytes(serialization.Encoding.PEM)


def _signed_message(payload: dict, message_type: str = "Notification"):
    key, certificate = _certificate()
    message = {
        "Type": message_type,
        "MessageId": "sns-event-123",
        "TopicArn": TOPIC_ARN,
        "Message": json.dumps(payload),
        "Timestamp": "2026-07-30T12:00:00.000Z",
        "SignatureVersion": "2",
        "SigningCertURL": CERTIFICATE_URL,
    }
    if message_type != "Notification":
        message["Token"] = "confirmation-token"
        message["SubscribeURL"] = (
            "https://sns.us-east-1.amazonaws.com/"
            "?Action=ConfirmSubscription"
        )
    canonical = SnsMessageVerifier.canonical_message(message)
    message["Signature"] = base64.b64encode(
        key.sign(canonical, padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    return message, certificate


def test_valid_sns_signature_is_accepted():
    message, certificate = _signed_message({"eventType": "Delivery"})
    verifier = SnsMessageVerifier(
        topic_arn=TOPIC_ARN,
        certificate_fetcher=lambda _: certificate,
    )

    verifier.verify(message)


def test_wrong_topic_and_untrusted_certificate_are_rejected():
    message, certificate = _signed_message({"eventType": "Delivery"})
    with pytest.raises(ValueError, match="topic"):
        SnsMessageVerifier(
            topic_arn="arn:aws:sns:us-east-1:123:wrong",
            certificate_fetcher=lambda _: certificate,
        ).verify(message)

    message["SigningCertURL"] = "https://attacker.example/certificate.pem"
    with pytest.raises(ValueError, match="certificate URL"):
        SnsMessageVerifier(
            topic_arn=TOPIC_ARN,
            certificate_fetcher=lambda _: certificate,
        ).verify(message)


def test_permanent_bounce_from_ses_suppresses_recipient():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "sns.db"
        TenantStore(database_path).initialize()
        EmailOutboxStore(database_path).initialize()
        suppressions = EmailSuppressionStore(database_path)
        suppressions.initialize()
        processor = SesSnsEventProcessor(suppressions)
        sns_message = {
            "MessageId": "sns-bounce-1",
            "Message": json.dumps(
                {
                    "notificationType": "Bounce",
                    "mail": {
                        "messageId": "ses-message-1",
                        "destination": ["bounced@example.com"],
                    },
                    "bounce": {
                        "bounceType": "Permanent",
                        "bounceSubType": "NoEmail",
                        "bouncedRecipients": [
                            {"emailAddress": "bounced@example.com"}
                        ],
                    },
                }
            ),
        }

        result = processor.process(sns_message)

        assert result["event_type"] == "permanent_bounce"
        assert suppressions.is_suppressed("bounced@example.com")


def test_transient_bounce_does_not_suppress_recipient():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "sns.db"
        TenantStore(database_path).initialize()
        EmailOutboxStore(database_path).initialize()
        suppressions = EmailSuppressionStore(database_path)
        suppressions.initialize()
        processor = SesSnsEventProcessor(suppressions)
        sns_message = {
            "MessageId": "sns-bounce-2",
            "Message": json.dumps(
                {
                    "eventType": "Bounce",
                    "mail": {
                        "messageId": "ses-message-2",
                        "destination": ["temporary@example.com"],
                    },
                    "bounce": {
                        "bounceType": "Transient",
                        "bouncedRecipients": [
                            {"emailAddress": "temporary@example.com"}
                        ],
                    },
                }
            ),
        }

        result = processor.process(sns_message)

        assert result["event_type"] == "temporary_bounce"
        assert not suppressions.is_suppressed("temporary@example.com")
