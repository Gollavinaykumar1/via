# backend/agents/hr_agent.py — VIA Phase 3: Human Resources Department

import time
import logging
from backend.core.llm_provider import llm

logger = logging.getLogger("AI-Digital-Company")


async def hr_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    start = time.time()
    logger.info(f"HR Agent | Task: {task[:60]}")

    context_block = ""
    if ceo_strategy:
        context_block += f"\nCEO Strategic Direction: {ceo_strategy}\n"
    if inter_context:
        context_block += f"\nContext from other departments:\n{inter_context}\n"

    prompt = f"""You are the Head of Human Resources at a top-tier tech MNC called VIA.
{context_block}
A new project has been assigned: {task}

Your job is to produce a complete HR plan for this project covering:

1. TEAM STRUCTURE: List all roles needed (job titles, seniority levels, team size)
2. JOB DESCRIPTIONS: Write 2-3 key job descriptions with responsibilities and requirements
3. ONBOARDING PLAN: 30/60/90 day onboarding plan for new hires
4. CULTURE & VALUES: Team culture guidelines and working principles
5. PERFORMANCE METRICS: KPIs and success metrics for the team
6. HIRING TIMELINE: Phased hiring plan with estimated dates
7. SALARY BUDGET: Approximate salary ranges per role (USD/year)
8. TEAM POLICIES: Remote work, meetings, code review, communication norms

Be specific, professional, and realistic. Format as a structured HR document.
Tailor everything specifically to the project described.
"""

    try:
        output = await llm.agenerate(prompt)
        duration = round(time.time() - start, 2)
        sections = _parse_hr_output(output or "")
        logger.info(f"HR Agent done | {duration}s")
        return {
            "department": "Human Resources",
            "status": "success",
            "execution_time_seconds": duration,
            "confidence": 0.91,
            "output": {
                "department": "Human Resources",
                "team_structure": sections.get("team_structure", ""),
                "job_descriptions": sections.get("job_descriptions", ""),
                "onboarding_plan": sections.get("onboarding_plan", ""),
                "culture_values": sections.get("culture_values", ""),
                "performance_metrics": sections.get("performance_metrics", ""),
                "hiring_timeline": sections.get("hiring_timeline", ""),
                "salary_budget": sections.get("salary_budget", ""),
                "team_policies": sections.get("team_policies", ""),
                "full_report": output or "",
                "summary": f"HR plan for '{task[:80]}' — covering team structure, hiring, onboarding, and culture.",
            },
        }

    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"HR Agent failed | {e}")
        return {
            "department": "Human Resources",
            "status": "failed",
            "execution_time_seconds": duration,
            "confidence": 0.0,
            "error": str(e),
            "output": {},
        }


def _parse_hr_output(text: str) -> dict:
    sections = {}
    keywords = {
        "team_structure": ["team structure", "roles", "team size"],
        "job_descriptions": ["job description", "responsibilities", "requirements"],
        "onboarding_plan": ["onboarding", "30/60/90", "day plan"],
        "culture_values": ["culture", "values", "principles"],
        "performance_metrics": ["kpi", "metrics", "performance"],
        "hiring_timeline": ["timeline", "hiring plan", "phases"],
        "salary_budget": ["salary", "budget", "compensation"],
        "team_policies": ["policy", "policies", "remote", "communication"],
    }
    lines = text.split("\n")
    current = "general"
    buckets = {k: [] for k in keywords}
    buckets["general"] = []
    for line in lines:
        ll = line.lower()
        for key, kws in keywords.items():
            if any(kw in ll for kw in kws):
                current = key
                break
        buckets.get(current, buckets["general"]).append(line)
    for key in keywords:
        sections[key] = "\n".join(buckets[key]).strip()
    return sections