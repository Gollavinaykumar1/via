# backend/core/tracer.py — Phase 2: includes inter-agent trace events
from datetime import datetime

class ExecutionTracer:
    def __init__(self):
        self.trace = []; self.start_time = ""; self.end_time = ""

    def start(self, task: str):
        self.start_time = datetime.now().isoformat()
        self.trace = []
        self._r("ORCHESTRATOR", "Task received", {"task": task})

    def add_memory_injection(self, count: int):
        self._r("CEO_AGENT", "Company memory injected", {"records_injected": count})

    def add_ceo_decision(self, short_term, long_term, departments):
        self._r("CEO_AGENT", "Strategic decision made", {
            "short_term_strategy": short_term,
            "long_term_vision": long_term,
            "departments_selected": departments
        })

    def add_inter_agent(self, from_agent: str, to_agents: list, summary: str):
        self._r("INTER_AGENT_BUS", f"Context: {from_agent} → {to_agents}", {
            "from": from_agent, "to": to_agents, "context_summary": summary[:150]
        })

    def add_scaling_decision(self, original, expanded, reason):
        self._r("SCALING_ENGINE", "Autonomous scaling triggered", {
            "original": original, "expanded": expanded, "reason": reason
        })

    def add_agent_result(self, name, status, duration, confidence):
        self._r(f"{name.upper()}_AGENT", f"Execution {status}", {
            "status": status, "duration_seconds": duration, "confidence": confidence
        })

    def finish(self, total_duration, success, failed):
        self.end_time = datetime.now().isoformat()
        self._r("ORCHESTRATOR", "Execution complete", {
            "started_at": self.start_time, "finished_at": self.end_time,
            "total_duration_seconds": total_duration,
            "agents_succeeded": success, "agents_failed": failed
        })

    def get_trace(self): return self.trace

    def _r(self, actor, event, data):
        self.trace.append({"timestamp": datetime.now().isoformat(), "actor": actor, "event": event, "data": data})
