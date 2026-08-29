from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class AssetState(StrEnum):
    INGESTED = "ingested"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MediaAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    state: AssetState
    download_url: str | None = None


class ProcessingJob(BaseModel):
    job_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    state: AssetState


class CreatorOrder(BaseModel):
    order_id: str = Field(min_length=1)
    creator_email: EmailStr
    amount_cents: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    asset: MediaAsset
    processing_job: ProcessingJob


class DeliveryResult(BaseModel):
    order_id: str
    delivery_state: str
    message_id: str | None = None
