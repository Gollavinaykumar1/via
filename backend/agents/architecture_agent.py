# backend/agents/architecture_agent.py — Phase 2: reads backend context
import json, re
from backend.core.llm_provider import llm
from backend.core.logger import logger

def _extract(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None

async def architecture_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    context_block = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""
    prompt = (
        "You are a Principal Systems Architect at an MNC-level tech company.\n\n"
        "CEO Strategic Direction: " + ceo_strategy + "\n"
        + context_block +
        "Analyze the business idea and return ONLY valid JSON:\n"
        '{"department":"System Architecture","design_pattern":{"primary":"...","rationale":"..."},'
        '"system_components":["..."],"data_flow":{"ingestion":"...","processing":"...","storage":"...","egress":"..."},'
        '"service_boundaries":["..."],"resilience":{"fault_tolerance":"...","disaster_recovery":"...","circuit_breaker":"..."},'
        '"scalability_path":"..."}\n\n'
        "Business idea: " + task + "\n"
    )
    logger.info("Architecture Agent | Generating plan...")
    raw = await llm.agenerate(prompt)
    parsed = _extract(raw)
    if parsed:
        parsed["department"] = "System Architecture"
        return parsed
    return {
        "department": "System Architecture",
        "design_pattern": {"primary": "Layered Monolith with modular boundaries.", "rationale": "Fastest to production. Enables future microservice extraction."},
        "system_components": ["API Gateway: routing + auth.", "Business Logic: stateless services.", "Data Layer: repository pattern."],
        "data_flow": {"ingestion": "Client → HTTPS → Gateway → Validation.", "processing": "Controller → Service → Domain.", "storage": "Repository → ORM → PostgreSQL + Redis.", "egress": "Pydantic JSON → Client."},
        "service_boundaries": ["Auth boundary: isolated AuthService.", "Domain boundary: no direct DB access."],
        "resilience": {"fault_tolerance": "Graceful degradation, no cascading failures.", "disaster_recovery": "RPO 1hr, RTO 30min.", "circuit_breaker": "Exponential backoff, max 3 retries."},
        "scalability_path": "MVP monolith → extract services → full microservice mesh."
    }
