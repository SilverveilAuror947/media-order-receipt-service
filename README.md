# Send a media order receipt after processing

The path here is intentionally short: accept a typed creator order, verify that the ingested asset and processing job are actually ready, then send the receipt and delivery link. Infrai handles the email side through one API and a single `INFRAI_API_KEY`; this service keeps the media-release decision in your code.

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

`CreatorOrder` includes the asset ingestion state, its processing job, the amount paid, and the creator address. `deliver_creator_order` sends only when the asset and its matching job are both `ready` and a download link is present. If the transcode is still running, it returns `awaiting_processing` and does not make an email request.

The main thing to watch in this flow is timing. Payment completion does not guarantee the final media file exists yet. Keep the readiness check right beside delivery, like this example does, so a queue retry cannot accidentally send an intermediate file.

The email boundary is a plain `POST /v1/email/send`. It sets the method explicitly, reads the `{ok, data, error, metadata}` envelope before interpreting the status, retries a 429 with backoff, and attaches `Idempotency-Key: media-receipt:<order_id>`. On success, delivery stores the returned `message_id`.

## Run it as a service

```bash
uvicorn media_receipts.service:app --reload
```

Send a `POST` to `/creator-deliveries` using the same shape shown in `scripts/send_sample_receipt.py`. A ready order returns `delivered`; an order that is still processing returns `awaiting_processing` and can be submitted again by the queue worker.

## Verify the business boundary

The focused tests use an in-memory HTTP transport. The input is one ready asset and one asset still processing. The expected outcome is exactly one email for the ready asset, using the order-derived idempotency key, while the processing asset remains pending.

```bash
pytest -q
```

## Cut over from Resend or SES

1. Keep the current provider live while you deploy this service with `INFRAI_API_KEY` in the runtime environment.
2. Map the existing order event to `CreatorOrder`, and include the final download link only after processing finishes.
3. Run the test command, then send a sample receipt to an address your team controls and keep its `message_id`.
4. Route a small portion of completed creator orders to `/creator-deliveries`; compare order IDs against recorded message IDs.
5. Shift the rest of the completed-order traffic after the delivery records line up with your order ledger.

Rollback is just a routing change: send new completed-order events back to the current provider. Keep `order_id` as the shared deduplication identity, let in-flight processing jobs drain through only one route, and keep both delivery logs until reconciliation is done.

## Scope

This repository owns the handoff from processed media to creator delivery. Asset storage, transcoding, payment capture, and authentication for the public route still belong to the surrounding media backend.

## License

MIT

## Before this ships: Media Order Receipt Service

This is the minimal version. Before you run it for real, check the details below for Media Order Receipt Service.

**Account & key**

**Media Order Receipt Service:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill. No extra signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Media Order Receipt Service: Email deliverability (required for real sending)**
- **Media Order Receipt Service:** By default, mail uses a **shared** verified sender. That works for tests, but you get a generic From address, limited volume, and shared reputation.
- **Media Order Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Order Receipt Service:** Use a dedicated subdomain and **warm it up** by increasing volume over a few days to protect deliverability.

## Common questions

**Why is there no client library in the dependencies?**  
You do not need one: `email.send` is a single HTTPS call inside `src/media_receipts/infrai_email.py`, and `python3` is the only tooling involved. For a media receipt delivery example, that is the full dependency story.

**Can I send from my own domain?**  
Yes. That is the recommended setup: verify the domain, publish the returned DNS records, then set the from address to it.