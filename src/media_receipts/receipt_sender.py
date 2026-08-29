from html import escape

from .infrai_email import InfraiEmailClient
from .models import AssetState, CreatorOrder, DeliveryResult


def receipt_html(order: CreatorOrder) -> str:
    amount = f"{order.amount_cents / 100:.2f} {escape(order.currency)}"
    title = escape(order.asset.title)
    link = escape(order.asset.download_url or "", quote=True)
    return (
        f"<h1>Your media order is ready</h1>"
        f"<p>Receipt for order {escape(order.order_id)}: {amount}</p>"
        f"<p>{title} has finished processing.</p>"
        f'<p><a href="{link}">Download creator delivery</a></p>'
    )


async def deliver_creator_order(
    order: CreatorOrder, client: InfraiEmailClient
) -> DeliveryResult:
    asset_matches_job = order.processing_job.asset_id == order.asset.asset_id
    ready = (
        order.asset.state is AssetState.READY
        and order.processing_job.state is AssetState.READY
        and order.asset.download_url is not None
        and asset_matches_job
    )
    if not ready:
        return DeliveryResult(order_id=order.order_id, delivery_state="awaiting_processing")

    message_id = await client.send_receipt(
        to=str(order.creator_email),
        subject=f"Receipt and delivery for {order.asset.title}",
        html=receipt_html(order),
        idempotency_key=f"media-receipt:{order.order_id}",
    )
    return DeliveryResult(
        order_id=order.order_id,
        delivery_state="delivered",
        message_id=message_id,
    )
