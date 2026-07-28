# backend/agents/security_agent.py — Phase 2: reads backend context
import json, re
from backend.core.llm_provider import llm
from backend.core.logger import logger

def _extract(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None

async def security_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    context_block = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""
    prompt = (
        "You are a Chief Security Officer at an MNC-level tech company.\n\n"
        "CEO Strategic Direction: " + ceo_strategy + "\n"
        + context_block +
        "Analyze the business idea and return ONLY valid JSON:\n"
        '{"department":"Security Engineering","threat_model":{"top_threats":["..."],"attack_surfaces":["..."]},'
        '"authentication":{"strategy":"...","token_management":"...","mfa":"..."},'
        '"encryption":{"in_transit":"...","at_rest":"...","key_management":"..."},'
        '"risk_mitigation":["..."],"compliance":["..."]}\n\n'
        "Business idea: " + task + "\n"
    )
    logger.info("Security Agent | Generating plan...")
    raw = await llm.agenerate(prompt)
    parsed = _extract(raw)
    if parsed:
        parsed["department"] = "Security Engineering"
        return parsed
    return {
        "department": "Security Engineering",
        "threat_model": {"top_threats": ["Unauthorized access", "Data exfiltration", "Injection attacks"], "attack_surfaces": ["Public API", "Auth layer", "DB"]},
        "authentication": {"strategy": "JWT access tokens (15min) + refresh tokens (7d).", "token_management": "Redis revocation list.", "mfa": "TOTP for admin accounts."},
        "encryption": {"in_transit": "TLS 1.3 + HSTS.", "at_rest": "AES-256 + bcrypt.", "key_management": "Env secrets, 90-day rotation."},
        "risk_mitigation": ["Rate limiting 100 req/min.", "Parameterized queries only.", "CORS restricted origins."],
        "compliance": ["OWASP Top 10", "GDPR"]
    }
