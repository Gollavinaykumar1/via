# backend/routers/meeting_router.py — VIA Phase 3: Meeting Room API

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.auth import get_current_active_user
from backend.core.meeting_engine import generate_meeting_fast, AGENT_PERSONAS
from backend.core.memory_store import save_meeting_transcript, get_meeting, get_recent_meetings

router = APIRouter(prefix="/meetings", tags=["Meetings"])


class MeetingRequest(BaseModel):
    task: str = Field(..., min_length=5, max_length=2000)
    departments: list = Field(default=["ceo", "backend", "frontend"])
    ceo_strategy: str = Field(default="Execute with speed and precision.")


@router.post("/generate/")
async def generate_meeting_endpoint(
    req: MeetingRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Generate a real-time agent meeting transcript for a given task."""
    job_id = str(uuid.uuid4())

    # Ensure ceo is always first
    depts = req.departments
    if "ceo" not in depts:
        depts = ["ceo"] + depts

    messages = await generate_meeting_fast(req.task, depts, req.ceo_strategy)

    # Save to DB
    await save_meeting_transcript(job_id, req.task, messages)

    return {
        "meeting_id": job_id,
        "task": req.task,
        "departments": depts,
        "messages": messages,
        "message_count": len(messages),
    }


# ── IMPORTANT: Specific routes BEFORE dynamic /{meeting_id}/ ──────────────────

@router.get("/personas/all")
async def get_personas(current_user: dict = Depends(get_current_active_user)):
    """Get all agent personas and their details."""
    return {
        "personas": {
            k: {
                "name": v["name"],
                "title": v["title"],
                "emoji": v["emoji"],
                "color": v["color"],
            }
            for k, v in AGENT_PERSONAS.items()
        }
    }


@router.get("/")
async def list_meetings(current_user: dict = Depends(get_current_active_user)):
    """List recent meetings."""
    meetings = await get_recent_meetings(limit=20)
    return {"meetings": meetings, "total": len(meetings)}


@router.get("/{meeting_id}/")
async def get_meeting_endpoint(
    meeting_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Retrieve a saved meeting transcript."""
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting
