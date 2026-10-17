"""Typed API contracts; validation never echoes rejected input."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchRequest(StrictModel):
    query: str = Field(max_length=256)


class ResetRequest(StrictModel):
    pass


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Record(BaseModel):
    id: int
    name: str
    description: str
    source: str


class SearchResponse(BaseModel):
    sql: str
    parameters: list[str]
    rows: list[Record]
    error: ErrorDetail | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ResetResponse(BaseModel):
    status: Literal["reset"] = "reset"


class ConfigResponse(BaseModel):
    csrf_token: str


class Example(BaseModel):
    label: str
    query: str
    explanation: str


EXAMPLES = [
    Example(
        label="Normal search", query="backpack", explanation="Both return one public product."
    ),
    Example(
        label="Literal apostrophe",
        query="Maker's",
        explanation="Fixed finds the notebook; unsafe SQL has a broken string literal.",
    ),
    Example(
        label="Boolean injection",
        query="' OR 1=1 -- ",
        explanation="Unsafe SQL matches all public products; fixed treats the payload as data.",
    ),
    Example(
        label="UNION injection",
        query="' UNION SELECT id, label, value, 'internal' FROM internal_records -- ",
        explanation="Unsafe SQL exposes synthetic internal records; fixed returns none.",
    ),
]
