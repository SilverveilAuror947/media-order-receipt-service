import json

import httpx
import pytest

from media_receipts.infrai_email import InfraiEmailClient
from media_receipts.models import CreatorOrder
from media_receipts.receipt_sender import deliver_creator_order


def make_order(asset_state: str = "ready", job_state: str = "ready") -> CreatorOrder:
    return CreatorOrder.model_validate(
        {
            "order_id": "ord_42",
            "creator_email": "editor@example.com",
            "amount_cents": 4900,
            "currency": "USD",
            "asset": {
                "asset_id": "asset_7",
                "title": "Concert Master",
                "state": asset_state,
                "download_url": "https://downloads.example.com/concert.mp4",
            },
            "processing_job": {
                "job_id": "job_9",
                "asset_id": "asset_7",
                "state": job_state,
            },
        }
    )


@pytest.mark.asyncio
async def test_ready_asset_sends_receipt_with_stable_order_key() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg_123"}})

    client = InfraiEmailClient(api_key="test-key", transport=httpx.MockTransport(handler))
    result = await deliver_creator_order(make_order(), client)

    assert result.delivery_state == "delivered"
    assert result.message_id == "msg_123"
    assert len(captured) == 1
    assert captured[0].method == "POST"
    assert captured[0].headers["Idempotency-Key"] == "media-receipt:ord_42"
    assert json.loads(captured[0].content)["to"] == "editor@example.com"


@pytest.mark.asyncio
async def test_processing_asset_waits_without_sending_email() -> None:
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected request: {request.method}")

    client = InfraiEmailClient(
        api_key="test-key", transport=httpx.MockTransport(unexpected_request)
    )
    result = await deliver_creator_order(make_order(job_state="processing"), client)

    assert result.delivery_state == "awaiting_processing"
    assert result.message_id is None
