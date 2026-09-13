"""Pydantic document models for Sentinel Shift Phase 1.

Follows MongoDB best practices: ``ObjectId`` is never leaked as a BSON type.
``PyObjectId`` coerces ``ObjectId`` -> ``str`` and ``BaseDocument`` maps
``_id`` <-> ``id`` with ``to_mongo()`` / ``from_mongo()`` helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _coerce_objectid(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    return value


PyObjectId = Annotated[str, BeforeValidator(_coerce_objectid)]


class BaseDocument(BaseModel):
    """Base for all persisted documents. Maps Mongo ``_id`` to ``id: str``."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> Dict[str, Any]:
        doc = self.model_dump(by_alias=True, exclude_none=False)
        if doc.get("_id") is None:
            doc.pop("_id", None)
        return doc

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]):
        if doc is None:
            return None
        return cls.model_validate(doc)


class Location(BaseModel):
    city: str
    country: str


class UserBaseline(BaseModel):
    active_start_minute: int
    active_end_minute: int
    resource_families: List[str]
    data_mb_baseline: List[float]
    file_count_baseline: List[int]
    rolling_30m_count_baseline: List[int]


class UserDoc(BaseDocument):
    user_id: str
    display_name: str
    location: Location
    user_timezone: str
    baseline: UserBaseline
    created_at: datetime


class EventDoc(BaseDocument):
    event_id: str
    user_id: str
    # Original provenance string exactly as ingested.
    timestamp_original: Optional[str] = None
    # Normalized UTC BSON datetime (None when the event is quarantined for a bad timestamp).
    timestamp_utc: Optional[datetime] = None
    user_timezone: Optional[str] = None
    location: Optional[Location] = None
    event_type: Optional[Any] = None
    resource_family: Optional[Any] = None
    sensitivity: Optional[str] = None
    data_mb: Optional[float] = None
    file_count: Optional[int] = None
    signals: Dict[str, float] = Field(default_factory=dict)
    # Validation / trust state.
    quarantined: bool = False
    quarantine_reasons: List[str] = Field(default_factory=list)
    incomplete: bool = False
    missing_components: List[str] = Field(default_factory=list)


class ContextDoc(BaseDocument):
    context_id: str
    user_id: str
    affected_signal_families: List[str]
    raw_reduction_points: float
    confidence: str
    start_utc: Optional[datetime] = None
    end_utc: Optional[datetime] = None
    reason: str


class AuditDoc(BaseDocument):
    """Append-only audit record. ``dismissed`` is a workflow flag ONLY and must
    never influence scoring, quarantine, or baseline eligibility."""

    audit_id: str
    user_id: str
    event_id: str
    risk_score: float
    severity: str
    created_at: datetime
    dismissed: bool = False
    dismissed_at: Optional[datetime] = None


class DemoStateDoc(BaseDocument):
    seed_version: str
    engine_version: str
    engine_checksum: str
    fixture_hash: str
    reset_time: datetime
    reset_duration_ms: float
    document_counts: Dict[str, int]
