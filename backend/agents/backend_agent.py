# backend/agents/backend_agent.py — Phase 2: reads inter-agent context
import json, re
from backend.core.llm_provider import llm
from backend.core.logger import logger


def _extract(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None


async def backend_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    context_block = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""
    prompt = (
        "You are a Principal Backend Engineer at an MNC-level tech company.\n\n"
        "CEO Strategic Direction: " + ceo_strategy + "\n"
        + context_block +
        "Analyze the business idea and return ONLY valid JSON:\n"
        '{"department":"Backend Engineering","architecture":"...","database":{"primary":"...","caching":"...","schema_approach":"..."},'
        '"api_design":{"style":"...","key_endpoints":["..."],"auth_integration":"..."},'
        '"services":["..."],"key_recommendations":["..."]}\n\n'
        "Business idea: " + task + "\n"
    )
    logger.info("Backend Agent | Generating plan...")
    raw = await llm.agenerate(prompt)
    parsed = _extract(raw)
    if parsed:
        parsed["department"] = "Backend Engineering"
        return parsed
    return {
        "department": "Backend Engineering",
        "architecture": "FastAPI with async modular service separation.",
        "database": {"primary": "PostgreSQL - ACID compliant.", "caching": "Redis for hot-path.", "schema_approach": "Normalized relational schema."},
        "api_design": {"style": "REST /api/v1/", "key_endpoints": ["POST /api/v1/users", "GET /api/v1/items/{id}"], "auth_integration": "JWT middleware."},
        "services": ["UserService", "CoreDomainService", "NotificationService"],
        "key_recommendations": ["Async/await throughout.", "Pydantic validation.", "asyncpg connection pooling."]
    }