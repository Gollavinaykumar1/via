# backend/agents/marketing_agent.py — VIA Phase 3: Marketing Department

import time
import logging
from backend.core.llm_provider import llm

logger = logging.getLogger("AI-Digital-Company")


async def marketing_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    start = time.time()
    logger.info(f"Marketing Agent | Task: {task[:60]}")

    context_block = ""
    if ceo_strategy:
        context_block += f"\nCEO Strategic Direction: {ceo_strategy}\n"
    if inter_context:
        context_block += f"\nContext from other departments:\n{inter_context}\n"

    prompt = f"""You are the Chief Marketing Officer (CMO) at a high-growth tech MNC called VIA.
{context_block}
A new product/project has been launched: {task}

Create a complete go-to-market strategy covering:

1. PRODUCT POSITIONING: Unique value proposition and market positioning statement
2. TARGET AUDIENCE: Detailed buyer personas (3 personas with demographics, pain points, goals)
3. BRAND IDENTITY: Brand name ideas, tagline options, tone of voice, brand colors
4. GO-TO-MARKET STRATEGY: Launch plan with phases and channels
5. CONTENT STRATEGY: Blog topics, social media plan, video content ideas
6. LANDING PAGE COPY: Hero headline, subheading, feature bullets, CTA text
7. SEO STRATEGY: Target keywords, content pillars, technical SEO priorities
8. GROWTH CHANNELS: Top 5 acquisition channels with expected CAC and conversion rates
9. COMPETITIVE ANALYSIS: 3 main competitors, their weaknesses, our differentiators
10. LAUNCH CAMPAIGN: 90-day marketing campaign plan with budget allocation
11. SUCCESS METRICS: Marketing KPIs, OKRs, and measurement framework

Be creative, data-driven, and specific. Write like a top-tier marketing strategist.
"""

    try:
        output = await llm.agenerate(prompt)
        duration = round(time.time() - start, 2)
        logger.info(f"Marketing Agent done | {duration}s")
        return {
            "department": "Marketing",
            "status": "success",
            "execution_time_seconds": duration,
            "confidence": 0.92,
            "output": {
                "department": "Marketing",
                "full_report": output or "",
                "summary": f"Go-to-market strategy for '{task[:80]}' — positioning, personas, campaigns, and growth.",
                "landing_page_copy": _extract_landing_copy(output or ""),
                "key_channels": _extract_channels(output or ""),
            },
        }

    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"Marketing Agent failed | {e}")
        return {
            "department": "Marketing",
            "status": "failed",
            "execution_time_seconds": duration,
            "confidence": 0.0,
            "error": str(e),
            "output": {},
        }


def _extract_landing_copy(text: str) -> dict:
    copy = {}
    lines = text.split("\n")
    for i, line in enumerate(lines):
        ll = line.lower()
        if "headline" in ll or "hero" in ll:
            if i + 1 < len(lines):
                copy["headline"] = lines[i + 1].strip()
        if "tagline" in ll or "subheading" in ll:
            if i + 1 < len(lines):
                copy["tagline"] = lines[i + 1].strip()
        if "cta" in ll or "call to action" in ll:
            if i + 1 < len(lines):
                copy["cta"] = lines[i + 1].strip()
    return copy


def _extract_channels(text: str) -> list:
    channels = []
    channel_keywords = [
        "SEO", "SEM", "Google Ads", "LinkedIn", "Twitter", "Instagram",
        "Facebook", "TikTok", "YouTube", "Email", "Content Marketing",
        "Influencer", "Affiliate", "Product Hunt", "Reddit", "Discord",
        "Developer Community", "Open Source", "Webinar", "Podcast"
    ]
    tl = text.lower()
    for ch in channel_keywords:
        if ch.lower() in tl:
            channels.append(ch)
    return channels[:8]