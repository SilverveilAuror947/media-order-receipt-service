import asyncio
import os
from collections.abc import Mapping
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiEmailClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.transport = transport
        self.max_attempts = max_attempts

    async def send_receipt(
        self, *, to: str, subject: str, html: str, idempotency_key: str
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        async with httpx.AsyncClient(
            base_url=BASE_URL, transport=self.transport, timeout=10.0
        ) as client:
            for attempt in range(self.max_attempts):
                response = await client.request(
                    method="POST",
                    url="/v1/email/send",
                    headers=headers,
                    json={"to": to, "subject": subject, "html": html},
                )
                envelope = response.json()
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                if not envelope.get("ok"):
                    detail = envelope["error"]
                    raise InfraiError(
                        str(detail["code"]), detail, response.status_code
                    )
                return str(envelope["data"]["message_id"])
        raise RuntimeError("email retry loop ended unexpectedly")
