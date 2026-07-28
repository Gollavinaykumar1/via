# backend/core/inter_agent_bus.py
# Phase 2: Inter-Agent Communication Bus
#
# Enables departments to share context with each other BEFORE final output.
# Example flow:
#   - backend finishes → shares API design summary → security reads it
#   - security finishes → shares threat model → devops reads it
#   - architecture finishes → shares system design → backend refines
#
# This makes the final output coherent, not just isolated reports.

from .logger import logger


class InterAgentBus:
    """
    Shared context store for agent-to-agent communication.
    Agents deposit summaries, other agents read them before generating output.
    """

    # Defines which agents read whose output
    # Format: {consumer: [producers it depends on]}
    DEPENDENCIES = {
        "security":     ["backend"],
        "devops":       ["backend", "architecture"],
        "ai_research":  ["architecture", "backend"],
        "architecture": ["backend"],
        "backend":      []
    }

    def __init__(self):
        self._context: dict[str, str] = {}

    def deposit(self, agent: str, summary: str):
        """Agent deposits a context summary after completing."""
        self._context[agent] = summary
        logger.info(f"InterAgentBus | deposit from: {agent} ({len(summary)} chars)")

    def get_context_for(self, agent: str) -> str:
        """
        Returns relevant context from upstream agents.
        Only includes agents this agent depends on.
        """
        deps = self.DEPENDENCIES.get(agent, [])
        parts = []
        for dep in deps:
            if dep in self._context:
                parts.append(f"[{dep.upper()} context]: {self._context[dep]}")
        if not parts:
            return ""
        result = "\n".join(parts)
        logger.info(f"InterAgentBus | {agent} received context from: {[d for d in deps if d in self._context]}")
        return result

    def has_context(self, agent: str) -> bool:
        return any(dep in self._context for dep in self.DEPENDENCIES.get(agent, []))

    def get_all(self) -> dict:
        return dict(self._context)

    def clear(self):
        self._context.clear()


def extract_summary(output: dict, agent_name: str) -> str:
    """
    Extract a concise summary from an agent's output for inter-agent sharing.
    """
    if not output or not isinstance(output, dict):
        return ""

    summary_parts = []

    if agent_name == "backend":
        arch = output.get("architecture", "")
        db   = output.get("database", {})
        api  = output.get("api_design", {})
        if arch: summary_parts.append(f"Architecture: {str(arch)[:100]}")
        if isinstance(db, dict): summary_parts.append(f"DB: {db.get('primary','')[:80]}")
        if isinstance(api, dict): summary_parts.append(f"API style: {api.get('style','')[:80]}")

    elif agent_name == "security":
        threats = output.get("threat_model", {})
        auth    = output.get("authentication", {})
        if isinstance(threats, dict): summary_parts.append(f"Top threats: {str(threats.get('top_threats',''))[:100]}")
        if isinstance(auth, dict): summary_parts.append(f"Auth: {auth.get('strategy','')[:80]}")

    elif agent_name == "architecture":
        pattern = output.get("design_pattern", {})
        flow    = output.get("data_flow", {})
        if isinstance(pattern, dict): summary_parts.append(f"Pattern: {pattern.get('primary','')[:100]}")
        if isinstance(flow, dict): summary_parts.append(f"Flow: {flow.get('ingestion','')[:80]}")

    elif agent_name == "devops":
        infra = output.get("infrastructure", {})
        cicd  = output.get("ci_cd", {})
        if isinstance(infra, dict): summary_parts.append(f"Cloud: {infra.get('cloud_provider','')[:80]}")
        if isinstance(cicd, dict): summary_parts.append(f"CI/CD: {cicd.get('pipeline_tool','')[:80]}")

    elif agent_name == "ai_research":
        model = output.get("model_strategy", {})
        if isinstance(model, dict): summary_parts.append(f"Model: {model.get('primary_model','')[:100]}")

    return " | ".join(summary_parts) if summary_parts else str(output)[:200]
