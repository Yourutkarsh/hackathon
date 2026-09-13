from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from sentinel import service


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# --------------------------------------------------------------------------- #
# Sentinel Shift V5.1 - Phase 2 endpoints                                      #
# Risk math is delegated entirely to the immutable risk_engine_v5_1 via        #
# sentinel.service / sentinel.scoring. Blocking pymongo calls run in a thread. #
# --------------------------------------------------------------------------- #
class InvestigateRequest(BaseModel):
    user_id: str
    event_id: Optional[str] = None


class AssistantChatRequest(BaseModel):
    user_id: str
    question: str
    event_id: Optional[str] = None


class AnalystActionRequest(BaseModel):
    user_id: str
    action: str
    event_id: Optional[str] = None
    note: Optional[str] = None


@api_router.get("/health")
async def health():
    return await run_in_threadpool(service.health_state)


@api_router.post("/demo/reset")
async def demo_reset():
    return await run_in_threadpool(service.reset)


@api_router.post("/demo/next-event")
async def demo_next_event(force: bool = False):
    result = await run_in_threadpool(service.next_event, force)
    if result.get("error") == "not_seeded":
        raise HTTPException(status_code=409, detail="Demo not seeded. Call /api/demo/reset first.")
    return result


@api_router.get("/users")
async def users_list():
    return await run_in_threadpool(service.list_users)


@api_router.get("/users/{user_id}")
async def users_get(user_id: str):
    user = await run_in_threadpool(service.get_user, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@api_router.get("/users/{user_id}/timeline")
async def users_timeline(user_id: str):
    timeline = await run_in_threadpool(service.get_timeline, user_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "events": timeline}


@api_router.get("/users/{user_id}/evidence")
async def users_evidence(user_id: str):
    result = await run_in_threadpool(service.user_evidence, user_id)
    if result.get("error") == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if result.get("error") == "no_trusted_events":
        raise HTTPException(status_code=422, detail="User has no trusted events")
    return result


@api_router.get("/users/{user_id}/alerts")
async def users_alerts(user_id: str):
    result = await run_in_threadpool(service.user_alerts, user_id)
    if result.get("error") == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")
    return result


@api_router.get("/evaluation")
async def evaluation():
    return await run_in_threadpool(service.evaluation)


@api_router.post("/investigate")
async def investigate(req: InvestigateRequest):
    result = await run_in_threadpool(service.investigate, req.user_id, req.event_id)
    err = result.get("error")
    if err == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if err == "event_not_found":
        raise HTTPException(status_code=404, detail="Event not found for user")
    if err == "no_trusted_events":
        raise HTTPException(status_code=422, detail="User has no trusted events to score")
    if err == "event_quarantined":
        raise HTTPException(status_code=422, detail={
            "message": "Event is quarantined and excluded from trusted scoring",
            "quarantine_reasons": result.get("quarantine_reasons", []),
        })
    return result


@api_router.post("/assistant/chat")
async def assistant_chat(req: AssistantChatRequest):
    return await run_in_threadpool(service.assistant_chat, req.user_id, req.question, req.event_id)


@api_router.get("/audit")
async def audit_list(user_id: Optional[str] = None):
    return {"records": await run_in_threadpool(service.list_audit, user_id)}


@api_router.post("/audit/action")
async def audit_action(req: AnalystActionRequest):
    result = await run_in_threadpool(
        service.analyst_action, req.user_id, req.event_id, req.action, req.note)
    err = result.get("error")
    if err == "invalid_action":
        raise HTTPException(status_code=400, detail="action must be NOTE, ESCALATE or DISMISS")
    if err == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if err == "event_not_found":
        raise HTTPException(status_code=404, detail="Event not found for user")
    if err in ("event_quarantined", "no_trusted_events"):
        raise HTTPException(status_code=422, detail=err)
    return result


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()