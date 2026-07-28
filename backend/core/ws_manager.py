# backend/core/ws_manager.py
# Phase 2: WebSocket Manager
# Manages all active WebSocket connections per job_id
# Broadcasts real-time streaming events to connected clients

import asyncio
import json
from datetime import datetime
from fastapi import WebSocket
from .logger import logger


class ConnectionManager:
    """
    Manages WebSocket connections grouped by job_id.
    Multiple clients can subscribe to the same job.
    """

    def __init__(self):
        # {job_id: [WebSocket, ...]}
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = []
        self._connections[job_id].append(websocket)
        logger.info(f"WS connected | job={job_id} | total={len(self._connections[job_id])}")

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self._connections:
            try:
                self._connections[job_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[job_id]:
                del self._connections[job_id]
        logger.info(f"WS disconnected | job={job_id}")

    async def broadcast(self, job_id: str, event: str, data: dict):
        """Send a structured event to all clients subscribed to a job."""
        if job_id not in self._connections:
            return

        message = json.dumps({
            "event":     event,
            "data":      data,
            "timestamp": datetime.now().isoformat(),
            "job_id":    job_id
        })

        dead = []
        for ws in self._connections[job_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(job_id, ws)

    async def send_step(self, job_id: str, step: str, message: str, data: dict = None):
        """Helper to send a pipeline step event."""
        await self.broadcast(job_id, "pipeline_step", {
            "step":    step,
            "message": message,
            "details": data or {}
        })

    async def send_agent_start(self, job_id: str, agent: str):
        await self.broadcast(job_id, "agent_start", {"agent": agent})

    async def send_agent_done(self, job_id: str, agent: str, status: str, duration: float, confidence: float, human_note: str = None):
        await self.broadcast(job_id, "agent_done", {
            "agent":      agent,
            "status":     status,
            "duration":   duration,
            "confidence": confidence,
            "human_note": human_note
        })

    async def send_ceo_decision(self, job_id: str, short_term: str, long_term: str, departments: list):
        await self.broadcast(job_id, "ceo_decision", {
            "short_term_strategy": short_term,
            "long_term_vision":    long_term,
            "departments":         departments
        })

    async def send_inter_agent(self, job_id: str, from_agent: str, to_agents: list, summary: str):
        await self.broadcast(job_id, "inter_agent_context", {
            "from":    from_agent,
            "to":      to_agents,
            "summary": summary[:200]
        })

    async def send_complete(self, job_id: str, result: dict):
        await self.broadcast(job_id, "complete", result)

    async def send_error(self, job_id: str, error: str):
        await self.broadcast(job_id, "error", {"error": error})

    async def send_self_correction(self, job_id: str, agent: str, note: str, attempt: int):
        """Broadcast a visible self-correction note from an agent in its own voice."""
        await self.broadcast(job_id, "self_correction", {
            "agent":   agent,
            "note":    note,
            "attempt": attempt,
        })



# Singleton instance
ws_manager = ConnectionManager()
