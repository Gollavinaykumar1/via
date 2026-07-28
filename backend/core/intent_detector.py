# backend/core/intent_detector.py — VIA Phase 5: 3-Mode Intent Detection
# Classifies user messages into: 'chat', 'build', or 'analyze'

import logging

logger = logging.getLogger("AI-Digital-Company")


def detect_intent(message: str) -> str:
    """
    Detect user intent from their message.
    Returns: 'chat', 'build', or 'analyze'
    """
    msg = message.lower().strip()

    # Very short messages are almost always chat
    if len(msg) < 8:
        return "chat"

    # ── Strong BUILD signals ──────────────────────────────────────────────
    strong_build = [
        "build me", "create me", "make me", "develop a", "develop me",
        "build a", "create a", "make a", "generate a", "generate me",
        "i want to build", "i need an app", "build an app", "create an app",
        "make an app", "build an application", "create an application",
        "deploy a", "deploy an", "launch a", "launch an",
        "start a project", "write an app", "code me", "code a",
        "i want an app", "i want a website", "i want a platform",
        "build this", "create this", "make this",
    ]
    if any(phrase in msg for phrase in strong_build):
        logger.info(f"Intent: BUILD (strong signal) | {msg[:60]}")
        return "build"

    # ── Strong ANALYZE signals ────────────────────────────────────────────
    strong_analyze = [
        "analyze my", "analyze the", "analyze this",
        "give me a business plan", "create a business plan",
        "security audit", "security review", "security analysis",
        "give me a plan", "create a plan", "make a plan",
        "what tech stack", "recommend a tech stack",
        "create a hiring plan", "hiring plan for",
        "evaluate my", "assess my", "review my",
    ]
    if any(phrase in msg for phrase in strong_analyze):
        logger.info(f"Intent: ANALYZE (strong signal) | {msg[:60]}")
        return "analyze"

    # ── Keyword scoring ───────────────────────────────────────────────────
    build_keywords = [
        "build", "create", "make", "develop", "generate", "code",
        "application", "app", "website", "platform", "system",
        "tool", "dashboard", "api", "backend", "frontend",
        "deploy", "launch", "project", "write an app",
        "todo", "tracker", "management", "portal",
    ]

    analyze_keywords = [
        "analyze", "analysis", "plan", "strategy", "review",
        "assess", "evaluate", "recommend", "suggest", "advise",
        "business plan", "roadmap", "architecture", "design",
        "security audit", "tech stack", "budget", "hiring",
        "competitive", "market research", "feasibility",
        "risk assessment", "cost analysis", "roi",
    ]

    build_score = sum(1 for kw in build_keywords if kw in msg)
    analyze_score = sum(1 for kw in analyze_keywords if kw in msg)

    # Need at least 2 keyword hits to avoid false positives
    if build_score >= 2 and build_score > analyze_score:
        logger.info(f"Intent: BUILD (score={build_score}) | {msg[:60]}")
        return "build"

    if analyze_score >= 2 and analyze_score > build_score:
        logger.info(f"Intent: ANALYZE (score={analyze_score}) | {msg[:60]}")
        return "analyze"

    # Default: chat mode
    logger.info(f"Intent: CHAT (default) | {msg[:60]}")
    return "chat"
