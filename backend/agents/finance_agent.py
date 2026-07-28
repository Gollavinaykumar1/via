# backend/agents/finance_agent.py — VIA Phase 3: Finance Department

import re
import time
import logging
from backend.core.llm_provider import llm

logger = logging.getLogger("AI-Digital-Company")


async def finance_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    start = time.time()
    logger.info(f"Finance Agent | Task: {task[:60]}")

    context_block = ""
    if ceo_strategy:
        context_block += f"\nCEO Strategic Direction: {ceo_strategy}\n"
    if inter_context:
        context_block += f"\nContext from other departments:\n{inter_context}\n"

    prompt = f"""You are the Chief Financial Officer (CFO) at a tech MNC called VIA.
{context_block}
A new project has been initiated: {task}

Produce a comprehensive financial plan covering:

1. PROJECT BUDGET BREAKDOWN: Itemized costs (infrastructure, dev tools, licenses, APIs)
2. ROI ANALYSIS: Expected return on investment with 6/12/24 month projections
3. COST OPTIMIZATION: Where to cut costs without sacrificing quality
4. REVENUE MODEL: How this project can generate revenue (SaaS, freemium, ads, etc.)
5. BURN RATE: Monthly operational costs estimate
6. FUNDING REQUIREMENTS: How much capital needed and for what milestones
7. FINANCIAL RISKS: Top 5 financial risks and mitigation strategies
8. BREAK-EVEN ANALYSIS: When the project becomes profitable
9. PRICING STRATEGY: Recommended pricing tiers with justification
10. FINANCIAL KPIs: Key financial metrics to track

Use realistic market numbers. Be specific with dollar amounts.
Format as a professional CFO financial report.
"""

    try:
        output = await llm.agenerate(prompt)
        duration = round(time.time() - start, 2)
        logger.info(f"Finance Agent done | {duration}s")
        return {
            "department": "Finance",
            "status": "success",
            "execution_time_seconds": duration,
            "confidence": 0.90,
            "output": {
                "department": "Finance",
                "full_report": output or "",
                "summary": f"Financial plan for '{task[:80]}' — covering budget, ROI, pricing, and risk.",
                "highlights": _extract_highlights(output or ""),
            },
        }

    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"Finance Agent failed | {e}")
        return {
            "department": "Finance",
            "status": "failed",
            "execution_time_seconds": duration,
            "confidence": 0.0,
            "error": str(e),
            "output": {},
        }


def _extract_highlights(text: str) -> dict:
    highlights = {}
    amounts = re.findall(r'\$[\d,]+(?:\.\d+)?(?:k|K|m|M)?', text)
    if amounts:
        highlights["mentioned_amounts"] = amounts[:10]
    pcts = re.findall(r'\d+(?:\.\d+)?%', text)
    if pcts:
        highlights["percentages"] = pcts[:8]
    periods = re.findall(r'\d+\s*(?:month|year|week|day)s?', text, re.IGNORECASE)
    if periods:
        highlights["time_periods"] = periods[:6]
    return highlights