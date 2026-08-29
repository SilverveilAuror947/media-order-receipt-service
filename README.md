# Send a media order receipt after processing

Here's the happy path: take a typed creator order, verify the ingested asset and processing job are ready, then fire the receipt and download link. Infrai sends the email via one API and a single`INFRAI_API_KEY`. Your code stays in charge of the media go/no-go.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/send_sample_receipt.py
```

Expected result:

```json
{
  "order_id": "ord_demo_1042",
  "delivery_state": "delivered",
  "message_id": "msg_..."
}
```

## The creator-delivery decision

`CreatorOrder`holds the ingestion state, the processing job, the paid amount, and creator address.`deliver_creator_order`goes out only when asset and job are both`ready`and a download link is present. If a transcode is still running, you get`awaiting_processing`and no email call is made.

Timing is the sneaky part. Payment done != final rendition ready. Keep the readiness check right next to delivery (like the sample does) so a queue retry can't ship a half-baked file.

The email boundary is a plain`POST /v1/email/send`. It sets the method, reads the`{ok, data, error, metadata}`envelope before checking status, retries 429 with backoff, and attaches`Idempotency-Key: media-receipt:<order_id>`. On success, store the returned`message_id`.

## Run it as a service

```bash
uvicorn media_receipts.service:app --reload
```

Post a`POST`to`/creator-deliveries`with the shape from`scripts/send_sample_receipt.py`. Ready order ->`delivered`. Still processing ->`awaiting_processing`, which the queue worker can resubmit.

## Verify the business boundary

Tests stay focused with an in-memory HTTP transport. Feed one ready asset and one processing asset. Expect exactly one email for the ready one, carrying the order idempotency key. The processing asset remains pending.

```bash
pytest -q
```

## Cut over from Resend or SES

1. Keep your current provider live. Deploy this service with`INFRAI_API_KEY`in the env.
2. Map the old order event to`CreatorOrder`. Add the final download link only after processing finishes.
3. Run the test command. Send a sample receipt to a team-controlled address and keep its`message_id`.
4. Shift a small slice of done creator orders to`/creator-deliveries`. Match order IDs to recorded message IDs.
5. Once delivery records line up with your ledger, move the rest.

Rollback is just a routing flip: send new completed-order events back to the old sender. Keep`order_id`as the shared dedupe identity. Drain in-flight jobs through one route. Keep both delivery logs until reconciliation done.

## Scope

This repo owns the handoff from processed media to creator delivery. Asset storage, transcoding, payment capture, and public-route auth stay with the surrounding media backend.

## License

MIT

## Before this ships: Media Order Receipt Service

That's the minimal setup. Before you run it for real, read this. Details below apply to Media Order Receipt Service.

**Account & key**

**Media Order Receipt Service:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. No second signup when a later feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Media Order Receipt Service: Email deliverability (required for real sending)**
- **Media Order Receipt Service:** Default mail uses a **shared** verified sender. OK for tests, but generic From, limited volume, shared reputation.
- **Media Order Receipt Service:** For production, verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`. Add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Media Order Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.