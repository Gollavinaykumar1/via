# backend/core/memory_store.py — Phase 3: Agent Memory (DB-mode agnostic)

import json
import logging
from backend.database.db import (
    save_agent_mem, get_agent_mem, get_all_mem,
    save_meeting_db, get_meeting_db, get_recent_meetings_db
)

logger = logging.getLogger("AI-Digital-Company")


async def save_agent_memory(agent: str, task: str, output_summary: str, confidence: float):
    """Save a memory entry for an agent after task completion."""
    try:
        await save_agent_mem(agent, task, output_summary, confidence)
        logger.info(f"Memory saved | agent={agent}")
    except Exception as e:
        logger.warning(f"Memory save failed | {e}")


async def get_agent_memory(agent: str, limit: int = 5) -> list:
    """Retrieve recent memories for an agent."""
    try:
        rows = await get_agent_mem(agent, limit)
        return [
            {
                "task": dict(r)["task"],
                "output_summary": dict(r)["output_summary"],
                "confidence": dict(r)["confidence"],
                "timestamp": str(dict(r).get("created_at", "")),
            }
            for r in (rows or [])
        ]
    except Exception as e:
        logger.warning(f"Memory fetch failed | {e}")
        return []


async def get_agent_memory_for_task(agent_name: str, task: str) -> dict:
    """Retrieve an agent's memory for a specific task."""
    try:
        from backend.database.db import get_agent_memory_for_task_db
        r = await get_agent_memory_for_task_db(agent_name, task)
        if not r:
            return {}
        return {
            "output_summary": dict(r)["output_summary"],
            "confidence": dict(r)["confidence"],
            "timestamp": str(dict(r).get("created_at", "")),
        }
    except Exception as e:
        logger.warning(f"Memory fetch for task failed | {e}")
        return {}


async def get_all_memories(limit: int = 50) -> list:
    """Retrieve all recent agent memories across all agents."""
    try:
        rows = await get_all_mem(limit)
        return [
            {
                "agent": dict(r)["agent_name"],
                "task": dict(r)["task"],
                "output_summary": dict(r)["output_summary"],
                "confidence": dict(r)["confidence"],
                "timestamp": str(dict(r).get("created_at", "")),
            }
            for r in (rows or [])
        ]
    except Exception as e:
        logger.warning(f"All memories fetch failed | {e}")
        return []


def build_memory_context(memories: list) -> str:
    """Format memory list into an LLM-injectable context string."""
    if not memories:
        return "No prior experience with this type of task."
    lines = []
    for i, m in enumerate(memories, 1):
        lines.append(
            f"Memory {i}: Task='{m['task'][:80]}' | "
            f"Result='{m['output_summary'][:120]}' | "
            f"Confidence={m['confidence']}"
        )
    return "\n".join(lines)


async def save_meeting_transcript(job_id: str, task: str, messages: list):
    """Save a meeting transcript to the database."""
    try:
        await save_meeting_db(job_id, task, json.dumps(messages), len(messages))
        logger.info(f"Meeting saved | job={job_id} | {len(messages)} messages")
    except Exception as e:
        logger.warning(f"Meeting save failed | {e}")


async def get_meeting(job_id: str) -> dict:
    """Retrieve a meeting transcript by job_id."""
    try:
        row = await get_meeting_db(job_id)
        if not row:
            return {}
        row = dict(row)
        return {
            "job_id": row["job_id"],
            "task": row["task"],
            "messages": json.loads(row["transcript"]) if row.get("transcript") else [],
            "message_count": row["message_count"],
            "timestamp": str(row.get("created_at", "")),
        }
    except Exception as e:
        logger.warning(f"Meeting fetch failed | {e}")
        return {}


async def get_recent_meetings(limit: int = 10) -> list:
    """Retrieve recent meeting summaries."""
    try:
        rows = await get_recent_meetings_db(limit)
        return [
            {
                "job_id": dict(r)["job_id"],
                "task": dict(r)["task"],
                "message_count": dict(r)["message_count"],
                "timestamp": str(dict(r).get("created_at", "")),
            }
            for r in (rows or [])
        ]
    except Exception as e:
        logger.warning(f"Recent meetings fetch failed | {e}")
        return []


async def check_agent_contradiction(agent_name: str, new_decision: str) -> str:
    """
    Phase 4: Check if the agent's new decision contradicts its last stored output.
    Uses string similarity heuristic — returns a first-person contradiction note if
    the content has changed significantly, or empty string if consistent.
    """
    try:
        memories = await get_agent_memory(agent_name, limit=1)
        if not memories:
            return ""
        last_summary = memories[0].get("output_summary", "")
        if not last_summary or len(last_summary) < 30:
            return ""
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, last_summary[:200], new_decision[:200]).ratio()
        if ratio < 0.3:
            short_last = last_summary[:80].rstrip()
            return (
                f"Actually, changing my earlier call on this — "
                f"last time I said '{short_last}...' but this build needs a different approach."
            )
        return ""
    except Exception as e:
        logger.warning(f"Contradiction check failed | {e}")
        return ""

