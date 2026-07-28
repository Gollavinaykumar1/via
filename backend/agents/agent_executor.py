# backend/agents/agent_executor.py — Phase 3: All 9 agents
import asyncio, time
from backend.agents.backend_agent      import backend_agent
from backend.agents.security_agent     import security_agent
from backend.agents.devops_agent       import devops_agent
from backend.agents.ai_research_agent  import ai_research_agent
from backend.agents.architecture_agent import architecture_agent
from backend.agents.frontend_agent     import frontend_agent
from backend.agents.hr_agent           import hr_agent
from backend.agents.finance_agent      import finance_agent
from backend.agents.marketing_agent    import marketing_agent
from backend.agents.presentation_agent import presentation_agent
from backend.core.inter_agent_bus      import InterAgentBus, extract_summary
from backend.core.meeting_engine       import run_pre_build_discussion
from backend.core.logger               import logger

AGENT_REGISTRY = {
    "backend":      backend_agent,
    "security":     security_agent,
    "devops":       devops_agent,
    "ai_research":  ai_research_agent,
    "architecture": architecture_agent,
    "frontend":     frontend_agent,
    "hr":           hr_agent,
    "finance":      finance_agent,
    "marketing":    marketing_agent,
    "presentation": presentation_agent,
}

EXECUTION_ORDER = [
    "architecture", "backend", "security", "devops", "ai_research",
    "frontend", "hr", "finance", "marketing", "presentation"
]


async def execute_agents(
    agent_names: list,
    task: str,
    ceo_strategy: str = "",
    project_brief: dict = None,        # ← NEW
    job_id: str = None,
    ws_manager=None
) -> dict:
    bus     = InterAgentBus()
    results = {}
    brief   = project_brief or {}      # ← NEW

    ordered = sorted(
        agent_names,
        key=lambda n: EXECUTION_ORDER.index(n) if n in EXECUTION_ORDER else 99
    )

    # Phase 1: Pre-build agent discussion
    if len(agent_names) > 1 and "backend" in agent_names:
        try:
            discussion = await run_pre_build_discussion(
                task, agent_names, ceo_strategy, ws_manager=ws_manager, job_id=job_id
            )
            logger.info(f"Pre-build discussion | {len(discussion)} exchanges")
        except Exception as e:
            logger.warning(f"Pre-build discussion skipped: {e}")

    for name in ordered:
        if name not in AGENT_REGISTRY:
            logger.warning(f"Agent not found: {name}")
            results[name] = {
                "status": "not_found",
                "error": f"'{name}' not in registry.",
                "execution_time_seconds": 0.0,
                "confidence": 0.0,
                "output": None
            }
            continue

        if ws_manager and job_id:
            await ws_manager.send_agent_start(job_id, name)

        inter_context = bus.get_context_for(name)
        if inter_context and ws_manager and job_id:
            deps = [d for d in bus.DEPENDENCIES.get(name, []) if d in bus.get_all()]
            await ws_manager.send_inter_agent(job_id, str(deps), [name], inter_context[:100])

        # ← passes project_brief to every agent
        name, result_data = await _run_agent(
            name,
            AGENT_REGISTRY[name],
            task,
            ceo_strategy,
            brief,              # ← NEW
            inter_context
        )
        # Extract human_note and handle clarification
        human_note = ""
        if result_data.get("output") and isinstance(result_data["output"], dict):
            human_note = result_data["output"].get("human_note", "")
            if result_data["output"].get("status") == "needs_clarification" or "needs_clarification" in result_data.get("status", "") or "needs_clarification" in human_note.lower():
                result_data["status"] = "needs_clarification"

        results[name] = result_data

        if result_data["status"] == "success" and result_data.get("output"):
            summary = extract_summary(result_data["output"], name)
            bus.deposit(name, summary)

        if ws_manager and job_id:
            await ws_manager.send_agent_done(
                job_id, name,
                result_data["status"],
                result_data["execution_time_seconds"],
                result_data["confidence"],
                human_note
            )

        await asyncio.sleep(7)  # 7s gap: safe for Groq (30 RPM) + Gemini (10 RPM)

    return results


async def _run_agent(
    name: str,
    agent_func,
    task: str,
    ceo_strategy: str,
    project_brief: dict,        # ← NEW
    inter_context: str
) -> tuple:
    start = time.time()
    try:
        result = await agent_func(
            task=task,
            project_brief=project_brief,   # ← NEW
            ceo_strategy=ceo_strategy,
            inter_context=inter_context
        )
        duration   = round(time.time() - start, 2)
        confidence = _confidence(result)
        logger.info(f"Agent OK | {name} | {duration}s | conf={confidence}")
        return name, {
            "status": "success",
            "execution_time_seconds": duration,
            "confidence": confidence,
            "output": result
        }
    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"Agent FAIL | {name} | {duration}s | {e}")
        return name, {
            "status": "failed",
            "execution_time_seconds": duration,
            "confidence": 0.0,
            "error": str(e),
            "output": None
        }


def _confidence(result: dict) -> float:
    if not result or not isinstance(result, dict): return 0.0
    total = sum(len(v) if isinstance(v, (dict, list)) else 1 for v in result.values())
    if total >= 15: return 0.97
    if total >= 10: return 0.92
    if total >= 6:  return 0.85
    if total >= 3:  return 0.72
    return 0.55