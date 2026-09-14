"""Standalone MongoDB reset module for Sentinel Shift Phase 1.

``reset_demo_db()`` is HTTP-independent and deterministic. It clears the demo
collections and bulk-inserts the frozen in-memory fixture. It NEVER regenerates
synthetic data. The warm-instance target is < 50 ms; a slower reset is reported
(not hidden) as a warning.
"""
from __future__ import annotations

import copy
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.database import Database

from .fixtures import (
    ENGINE_VERSION,
    SEED_VERSION,
    document_counts,
    fixture_hash,
    get_fixture,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

ENGINE_PATH = ROOT_DIR / "risk_engine_v5_1.py"
# Recorded immutable-engine checksum (import/checksum contract). If the engine
# is re-vendored, this must be updated intentionally.
ENGINE_CHECKSUM = "08446a7cf59a88eeff2d4bf492c6e30a2bb46316e884f098a5a6a3bf7f091c71"

DEMO_COLLECTIONS = ("users", "events", "contexts", "demo_state", "audit_records")
RESET_TARGET_MS = 50.0

_CLIENT: Optional[MongoClient] = None


def get_client() -> MongoClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = MongoClient(os.environ["MONGO_URL"])
    return _CLIENT


def get_db(db: Optional[Database] = None) -> Database:
    if db is not None:
        return db
    return get_client()[os.environ["DB_NAME"]]


def compute_engine_checksum() -> str:
    return hashlib.sha256(ENGINE_PATH.read_bytes()).hexdigest()


def verify_engine_integrity() -> bool:
    """True when the on-disk engine file matches the recorded immutable checksum."""
    return compute_engine_checksum() == ENGINE_CHECKSUM


def ensure_indexes(db: Optional[Database] = None) -> Dict[str, list]:
    """Create the deterministic compound + supporting indexes (idempotent)."""
    database = get_db(db)
    database["events"].create_index(
        [("timestamp_utc", ASCENDING), ("user_id", ASCENDING), ("event_id", ASCENDING)],
        name="ts_user_event",
    )
    database["events"].create_index([("event_id", ASCENDING)], name="event_id_unique", unique=True)
    database["events"].create_index([("user_id", ASCENDING)], name="events_user_id")
    database["users"].create_index([("user_id", ASCENDING)], name="users_user_id_unique", unique=True)
    database["contexts"].create_index([("user_id", ASCENDING)], name="contexts_user_id")
    database["audit_records"].create_index([("user_id", ASCENDING)], name="audit_user_id")
    database["audit_records"].create_index([("event_id", ASCENDING)], name="audit_event_id")
    database["audit_records"].create_index([("created_at", ASCENDING)], name="audit_created_at")
    return {c: [ix["name"] for ix in database[c].list_indexes()] for c in DEMO_COLLECTIONS}


def next_baseline_version(database: Optional[Database] = None) -> int:
    """Atomically increment and return the demo-wide ``baseline_version``.

    The counter lives in its own ``demo_counters`` document (never deleted by a
    reset) and is bumped with an atomic ``$inc`` upsert, so concurrent resets
    cannot lose or duplicate a version. ``demo_state`` mirrors the value.
    """
    database = get_db(database)
    doc = database["demo_counters"].find_one_and_update(
        {"_id": "baseline_version"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int((doc or {}).get("value", 1))


def current_baseline_version(database: Optional[Database] = None) -> int:
    """Read the persisted demo-wide baseline version (0 before the first reset)."""
    database = get_db(database)
    state = database["demo_state"].find_one({}, {"baseline_version": 1})
    if state and state.get("baseline_version") is not None:
        return int(state["baseline_version"])
    counter = database["demo_counters"].find_one({"_id": "baseline_version"})
    return int((counter or {}).get("value", 0))


def reset_demo_db(db: Optional[Database] = None) -> Dict[str, Any]:
    """Clear + reseed the demo collections from the frozen fixture.

    Returns a report with timing, document counts, fixture hash, engine version,
    the incremented demo-wide ``baseline_version``, and a performance-warning
    flag. Synthetic data is NEVER regenerated here.
    """
    database = get_db(db)
    ensure_indexes(database)

    fixture = get_fixture()  # deep copy: insert_many mutates docs with _id
    counts = document_counts()

    reset_time = datetime.now(timezone.utc)

    # Timed warm path: bump the demo-wide baseline version, clear the demo
    # collections, and bulk insert. The atomic counter upsert is INSIDE the timed
    # region so the reported duration reflects the entire reset (target < 50 ms).
    start = time.perf_counter()
    baseline_version = next_baseline_version(database)
    for coll in DEMO_COLLECTIONS:
        database[coll].delete_many({})
    if fixture["users"]:
        database["users"].insert_many(copy.deepcopy(fixture["users"]))
    if fixture["events"]:
        database["events"].insert_many(copy.deepcopy(fixture["events"]))
    if fixture["contexts"]:
        database["contexts"].insert_many(copy.deepcopy(fixture["contexts"]))
    # audit_records intentionally starts empty (append-only, generated at runtime).
    duration_ms = (time.perf_counter() - start) * 1000.0

    fx_hash = fixture_hash()
    demo_state = {
        "seed_version": SEED_VERSION,
        "engine_version": ENGINE_VERSION,
        "engine_checksum": compute_engine_checksum(),
        "fixture_hash": fx_hash,
        "reset_time": reset_time,
        "reset_duration_ms": round(duration_ms, 3),
        "document_counts": counts,
        # Scripted-demo cursor: number of trusted events already revealed.
        "cursor": 0,
        "paused": False,
        # Demo-wide baseline lifecycle version (increments on every reset).
        "baseline_version": baseline_version,
    }
    database["demo_state"].insert_one(copy.deepcopy(demo_state))

    performance_ok = duration_ms <= RESET_TARGET_MS
    report = {
        "fixture_hash": fx_hash,
        "document_counts": counts,
        "reset_duration_ms": round(duration_ms, 3),
        "reset_target_ms": RESET_TARGET_MS,
        "performance_ok": performance_ok,
        "engine_version": ENGINE_VERSION,
        "engine_checksum": demo_state["engine_checksum"],
        "engine_integrity_ok": demo_state["engine_checksum"] == ENGINE_CHECKSUM,
        "reset_time": reset_time.isoformat(),
        "baseline_version": baseline_version,
    }
    if not performance_ok:
        report["performance_warning"] = (
            f"reset took {duration_ms:.3f} ms (> {RESET_TARGET_MS} ms warm target)"
        )
    return report


if __name__ == "__main__":  # manual invocation: python -m sentinel.demo_db
    import json

    print(json.dumps(reset_demo_db(), indent=2))
