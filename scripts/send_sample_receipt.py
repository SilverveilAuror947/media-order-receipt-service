import asyncio
import json

from media_receipts.infrai_email import InfraiEmailClient
from media_receipts.models import CreatorOrder
from media_receipts.receipt_sender import deliver_creator_order


async def main() -> None:
    order = CreatorOrder.model_validate(
        {
            "order_id": "ord_demo_1042",
            "creator_email": "chenhua@changba.com",
            "amount_cents": 4900,
            "currency": "USD",
            "asset": {
                "asset_id": "asset_final_cut",
                "title": "Studio Session Final Cut",
                "state": "ready",
                "download_url": "https://downloads.example.com/studio-session-final.mp4",
            },
            "processing_job": {
                "job_id": "job_transcode_88",
                "asset_id": "asset_final_cut",
                "state": "ready",
            },
        }
    )
    result = await deliver_creator_order(order, InfraiEmailClient())
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
