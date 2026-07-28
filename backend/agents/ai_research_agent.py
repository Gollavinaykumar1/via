# backend/agents/ai_research_agent.py — Phase 2: reads architecture + backend context
import json, re
from backend.core.llm_provider import llm
from backend.core.logger import logger

def _extract(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None

async def ai_research_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    context_block = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""
    prompt = (
        "You are a Chief AI Research Scientist at an MNC-level tech company.\n\n"
        "CEO Strategic Direction: " + ceo_strategy + "\n"
        + context_block +
        "Analyze the business idea and return ONLY valid JSON:\n"
        '{"department":"AI Research","model_strategy":{"primary_model":"...","fallback_model":"...","deployment":"..."},'
        '"prompt_engineering":{"approach":"...","optimization":"...","guardrails":"..."},'
        '"fine_tuning":{"recommended":true,"reasoning":"...","data_requirements":"..."},'
        '"future_roadmap":["..."],"performance_targets":{"latency":"...","accuracy":"...","cost":"..."}}\n\n'
        "Business idea: " + task + "\n"
    )
    logger.info("AI Research Agent | Generating plan...")
    raw = await llm.agenerate(prompt)
    parsed = _extract(raw)
    if parsed:
        parsed["department"] = "AI Research"
        return parsed
    return {
        "department": "AI Research",
        "model_strategy": {"primary_model": "llama3 via Ollama.", "fallback_model": "GPT-4o.", "deployment": "Local dev, cloud prod."},
        "prompt_engineering": {"approach": "Chain-of-thought + zero-shot.", "optimization": "30% token reduction.", "guardrails": "JSON schema validation."},
        "fine_tuning": {"recommended": False, "reasoning": "Base model sufficient initially.", "data_requirements": "10k+ labeled examples."},
        "future_roadmap": ["Multi-agent reasoning.", "RAG integration.", "A/B model testing."],
        "performance_targets": {"latency": "Sub-3s p95.", "accuracy": ">95% JSON parse.", "cost": "<$0.01/request."}
    }
