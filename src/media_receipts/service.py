from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmailClient, InfraiError
from .models import CreatorOrder, DeliveryResult
from .receipt_sender import deliver_creator_order

app = FastAPI(title="Media receipt delivery")


@app.post("/creator-deliveries", response_model=DeliveryResult)
async def create_creator_delivery(order: CreatorOrder) -> DeliveryResult:
    try:
        return await deliver_creator_order(order, InfraiEmailClient())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": exc.detail.get("message", exc.code)},
        ) from exc
