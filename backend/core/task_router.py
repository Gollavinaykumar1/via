# backend/core/task_router.py
# Smart Task Router — detects task type and routes correctly

# ── Task Type Constants ───────────────────────────────────────────────────────
TECH_MODE     = "tech"
RESEARCH_MODE = "research"
BUSINESS_MODE = "business"
CREATIVE_MODE = "creative"
MATH_MODE     = "math"
GENERAL_MODE  = "general"

# ── Keyword Maps ─────────────────────────────────────────────────────────────
TECH_KEYWORDS = [
    "build", "create", "develop", "code", "program", "api",
    "backend", "frontend", "database", "deploy", "docker",
    "server", "app", "application", "website", "system",
    "microservice", "endpoint", "rest", "graphql", "fastapi",
    "django", "flask", "react", "node", "python", "javascript",
    "implement", "design a system", "architecture for",
    "authentication system", "login system", "crud"
]

RESEARCH_KEYWORDS = [
    "explain", "what is", "what are", "how does", "why is",
    "summarize", "summary", "describe", "define", "tell me about",
    "teach me", "help me understand", "notes on", "study",
    "difference between", "compare", "history of", "explain me",
    "what do you know about", "give me information"
]

BUSINESS_KEYWORDS = [
    "business plan", "marketing", "strategy", "startup",
    "revenue", "profit", "customer", "market research",
    "business model", "pitch", "investor", "sales",
    "branding", "product launch", "go to market"
]

CREATIVE_KEYWORDS = [
    "write a story", "poem", "script", "creative",
    "fiction", "novel", "blog post", "article",
    "write about", "generate a story", "essay"
]

MATH_KEYWORDS = [
    "solve", "calculate", "equation", "math",
    "algebra", "geometry", "calculus", "statistics",
    "probability", "formula", "compute", "integral",
    "derivative", "matrix", "theorem"
]


def detect_task_type(task: str) -> str:
    """
    Detect what type of task the user is asking for.
    Returns one of: tech, research, business, creative, math, general
    """
    task_lower = task.lower().strip()

    for keyword in TECH_KEYWORDS:
        if keyword in task_lower:
            return TECH_MODE

    for keyword in MATH_KEYWORDS:
        if keyword in task_lower:
            return MATH_MODE

    for keyword in BUSINESS_KEYWORDS:
        if keyword in task_lower:
            return BUSINESS_MODE

    for keyword in CREATIVE_KEYWORDS:
        if keyword in task_lower:
            return CREATIVE_MODE

    for keyword in RESEARCH_KEYWORDS:
        if keyword in task_lower:
            return RESEARCH_MODE

    return GENERAL_MODE


def get_mode_prompt(task_type: str, task: str) -> str:
    """
    Returns simple, direct prompts that work well with Ollama local models.
    Keep prompts short and direct — Ollama handles these best.
    """
    if task_type == MATH_MODE:
        return f"Solve this step by step and show all working: {task}"

    elif task_type == RESEARCH_MODE:
        return f"Explain this clearly with examples: {task}"

    elif task_type == BUSINESS_MODE:
        return f"Write a detailed business response for: {task}"

    elif task_type == CREATIVE_MODE:
        return f"Write creative content for: {task}"

    else:
        return f"Answer this helpfully and clearly: {task}"


def is_tech_task(task: str) -> bool:
    """Quick check — is this a tech/coding task?"""
    return detect_task_type(task) == TECH_MODE
