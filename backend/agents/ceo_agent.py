# backend/agents/ceo_agent.py
import json
import re
from backend.core.llm_provider import llm
from backend.core.config import VALID_DEPARTMENTS, MEMORY_INJECTION_COUNT
from backend.core.logger import logger


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def build_memory(history):
    if not history:
        return "No prior company history."
    lines = []
    for i, r in enumerate(history[:MEMORY_INJECTION_COUNT], 1):
        task = r.get("task", "")
        res = r.get("result", {})
        if isinstance(res, dict):
            strat = res.get("ceo_strategy", {})
            short = strat.get("short_term_strategy", "") if isinstance(strat, dict) else ""
            depts = res.get("selected_departments", [])
            lines.append(f"Run {i}: Task='{task[:80]}' | Strategy='{short[:60]}' | Depts={depts}")
        else:
            lines.append(f"Run {i}: Task='{task[:80]}'")
    return "\n".join(lines)


async def ceo_agent(task: str, history: list = None) -> dict:
    # history is passed in from main.py which fetches it async before calling this
    memory = build_memory(history or [])
    prompt = (
        "You are the CEO of an AI-powered autonomous MNC-level digital company.\n\n"
        "COMPANY MEMORY:\n" + memory + "\n\n"
        "DEPARTMENTS AVAILABLE:\n"
        "--- TECH DIVISION ---\n"
        "- backend: APIs, databases, services, server-side logic\n"
        "- frontend: React/Vite UI, responsive design, user experience\n"
        "- security: Auth, encryption, threats, compliance, pen testing\n"
        "- devops: Infrastructure, CI/CD, Docker, Kubernetes, cloud scaling\n"
        "- ai_research: LLM strategy, ML models, AI integration, optimization\n"
        "- architecture: System design, microservices, data flow, resilience\n"
        "--- BUSINESS DIVISION ---\n"
        "- hr: Job descriptions, team structure, onboarding, org planning\n"
        "- finance: Cost estimates, ROI analysis, budget breakdown, pricing\n"
        "- marketing: Landing page copy, go-to-market, brand, user acquisition\n\n"
        "Rules:\n"
        "- Select ONLY departments GENUINELY needed for this specific task\n"
        "- A tech product ALWAYS needs at least: backend + frontend\n"
        "- Add security, devops for production apps\n"
        "- Add hr/finance/marketing for business/startup ideas\n"
        "- Return ONLY valid JSON, no extra text:\n"
        "{\n"
        "  \"short_term_strategy\": \"0-3 month concrete execution plan\",\n"
        "  \"long_term_vision\": \"6-24 month product direction\",\n"
        "  \"departments\": [\"dept1\", \"dept2\", ...]\n"
        "}\n\n"
        "Task / Business Idea:\n" + task + "\n"
    )
    logger.info(f"CEO Agent | Task: {task[:80]}...")
    raw = await llm.agenerate(prompt)
    parsed = extract_json(raw)
    if parsed:
        selected = [d for d in parsed.get("departments", []) if d in VALID_DEPARTMENTS]
        if not selected:
            selected = ["backend"]
        logger.info(f"CEO decision | Departments: {selected}")
        return {
            "short_term_strategy": parsed.get("short_term_strategy", "Begin core development."),
            "long_term_vision":    parsed.get("long_term_vision", "Build a scalable product."),
            "departments":         selected,
            "_raw_llm_response":   raw,
            "_extracted_json":     parsed
        }
    return {
        "short_term_strategy": "Execute core development immediately.",
        "long_term_vision":    "Build a scalable, secure, full-stack product.",
        "departments":         ["backend", "frontend"],
        "_raw_llm_response":   raw,
        "_extracted_json":     {}
    }