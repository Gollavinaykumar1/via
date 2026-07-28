# backend/core/scaling_engine.py
from .config import VALID_DEPARTMENTS, COMPLEX_TASK_THRESHOLD
from .logger import logger

# Departments that are ESSENTIAL for building a full-stack app.
# HR, Finance, Marketing, AI Research, Architecture, DevOps just waste
# API credits and add 60+ minutes of delay without contributing code.
CORE_BUILD_DEPARTMENTS = ["backend", "frontend"]

def analyze_complexity(task):
    wc = len(task.split())
    hits = sum(1 for s in ["enterprise","large scale","distributed","microservices","high availability","real-time","millions","global","compliance","regulated","mission critical","fault tolerant","zero downtime","multi-region"] if s in task.lower())
    return "complex" if wc > COMPLEX_TASK_THRESHOLD or hits >= 3 else "moderate" if wc > 30 or hits >= 1 else "simple"

def autonomous_scale(task, ceo_departments):
    # Always restrict to only backend + frontend for build tasks.
    # The CEO tends to hallucinate unnecessary business agents (HR, Finance,
    # Marketing) which add 60+ minutes and produce zero code.
    reason = "Locked to core build agents (backend + frontend) for speed."
    logger.info(f"Scaling: CORE_ONLY | {reason}")
    return CORE_BUILD_DEPARTMENTS, False, reason
