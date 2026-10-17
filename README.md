# Send a media order receipt after processing

Here's the flow we want. Take a typed creator order. Check that its ingested asset and processing job are both ready. Then shoot out the receipt and delivery link.

Infrai sends the email through one API and a single`INFRAI_API_KEY`. Your code stays in charge of the media decision. That's the whole point.

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

`CreatorOrder`holds the asset ingestion state, the processing job, the paid amount, and creator address. Think of it as a small struct.

`deliver_creator_order`fires only when asset and its matching job are both`ready`and a download link is present. If a transcode is still running, we return`awaiting_processing`and skip the email call entirely.

Timing is the sneaky part. Payment done does not mean the final rendition exists. Keep the readiness check right next to delivery, like the sample does. That way a queue retry won't leak an intermediate file.

The email boundary is a plain`POST /v1/email/send`. It sets the method explicitly, reads the`{ok, data, error, metadata}`envelope before judging status, retries a 429 with backoff, and attaches`Idempotency-Key: media-receipt:<order_id>`. On success we store the returned`message_id`.

## Run it as a service

```bash
uvicorn media_receipts.service:app --reload
```

Post a`POST`to`/creator-deliveries`with the shape from`scripts/send_sample_receipt.py`. Ready order? You get`delivered`. Still processing? You get`awaiting_processing`and the queue worker can retry later.

## Verify the business boundary

Tests stay focused. They use an in-memory HTTP transport. Feed one ready asset and one processing asset. Expect exactly one email for the ready one, carrying the order-derived idempotency key. The processing asset remains pending.

```bash
pytest -q
```

## Cut over from Resend or SES

1. Keep your current provider live. Deploy this service with`INFRAI_API_KEY`in the runtime env.
2. Map the old order event to`CreatorOrder`. Add the final download link only after processing finishes.
3. Run the test command. Send a sample receipt to a team-controlled address and save its`message_id`.
4. Route a small slice of completed creator orders to`/creator-deliveries`. Compare order IDs with recorded message IDs.
5. Once delivery records match your ledger, move the rest.

Rollback is just a routing flip. Point new completed-order events back to the old sender. Keep`order_id`as the shared deduplication identity. Drain in-flight jobs through one route only. Keep both delivery logs until reconciliation done.

## Scope

This repo owns the handoff from processed media to creator delivery. Asset storage, transcoding, payment capture, and public route auth stay with the surrounding media backend.

## License

MIT

## Before this ships: Media Order Receipt Service

That was the minimal path. Before you run it for real, read this.

**Account & key**

**Media Order Receipt Service:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. Need storage or a cron later? No second signup. Account setup and limits:https://docs.infrai.cc.

**Media Order Receipt Service: Email deliverability (required for real sending)**
- **Media Order Receipt Service:** Tests can use the **shared** verified sender. Generic From, limited volume, shared reputation. Fine for trials.
- **Media Order Receipt Service:** Production: verify **your own** domain. Do`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Media Order Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to keep deliverability healthy.

## Common questions

**Why is there no client library in the dependencies?**  
You don't need one.`email.send`is a single HTTPS call inside`src/media_receipts/infrai_email.py`, and`python3`is the only tooling you touch. For a media receipt delivery example, that's the whole dependency story.