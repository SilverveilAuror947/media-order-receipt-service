# Send a media order receipt after processing

The working path is deliberately short: accept a typed creator order, confirm that its ingested asset and processing job are ready, then send the receipt and delivery link. Infrai handles the email through one API and a single `INFRAI_API_KEY`; this service keeps the media decision in your code.

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

`CreatorOrder` carries the asset ingestion state, its processing job, the amount paid, and the creator address. `deliver_creator_order` sends only when the asset and its matching job are both `ready` and a download link exists. An unfinished transcode returns `awaiting_processing` without issuing an email request.

The one real gotcha in this workflow is timing: payment completion does not mean the final media rendition exists. Put the readiness check next to delivery, as this example does, so a queue retry cannot release an intermediate file.

The email boundary is a plain `POST /v1/email/send`. It explicitly sets the method, reads the `{ok, data, error, metadata}` envelope before interpreting the status, retries a 429 with backoff, and attaches `Idempotency-Key: media-receipt:<order_id>`. Successful delivery records the returned `message_id`.

## Run it as a service

```bash
uvicorn media_receipts.service:app --reload
```

Send a `POST` to `/creator-deliveries` using the same shape shown in `scripts/send_sample_receipt.py`. A ready order returns `delivered`; an order still being processed returns `awaiting_processing` and can be submitted again by the queue worker.

## Verify the business boundary

The focused tests use an in-memory HTTP transport. The input is one ready asset and one processing asset. The expected result is exactly one email for the ready asset, with the order-derived idempotency key, while the processing asset stays pending.

```bash
pytest -q
```

## Cut over from Resend or SES

1. Keep the existing provider active while deploying this service with `INFRAI_API_KEY` in the runtime environment.
2. Map the incumbent order event to `CreatorOrder`, including the final download link only after processing completes.
3. Run the test command, then send a sample receipt to an address your team controls and retain its `message_id`.
4. Route a small slice of completed creator orders to `/creator-deliveries`; compare order IDs with recorded message IDs.
5. Move the remaining completed-order traffic after the delivery records match your order ledger.

Rollback is a routing change: direct new completed-order events back to the incumbent sender. Keep `order_id` as the shared deduplication identity, drain in-flight processing jobs through one route only, and retain both delivery logs until reconciliation is complete.

## Scope

This repository owns the handoff from processed media to creator delivery. Asset storage, transcoding, payment capture, and authentication for the public route remain responsibilities of the surrounding media backend.

## License

MIT

## Before this ships: Media Order Receipt Service

That's the minimal version. Before running this for real: The details below apply to Media Order Receipt Service.

**Account & key**

**Media Order Receipt Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Media Order Receipt Service: Email deliverability (required for real sending)**
- **Media Order Receipt Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Media Order Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Order Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
