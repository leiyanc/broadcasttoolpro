import json

from fastapi import APIRouter, HTTPException, Request

from backend.services.sns_email_events import (
    SesSnsEventProcessor,
    SnsMessageVerifier,
    confirm_sns_subscription,
)


router = APIRouter(
    prefix="/api/email-events",
    tags=["Email Events"],
)


@router.post("/amazon-sns")
async def amazon_sns_email_event(request: Request):
    try:
        message = json.loads(await request.body())
        SnsMessageVerifier().verify(message)
        message_type = message["Type"]
        if message_type == "SubscriptionConfirmation":
            confirm_sns_subscription(message["SubscribeURL"])
            return {"accepted": True, "subscription_confirmed": True}
        if message_type == "UnsubscribeConfirmation":
            return {"accepted": True, "unsubscribe_confirmed": True}
        return SesSnsEventProcessor().process(message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
