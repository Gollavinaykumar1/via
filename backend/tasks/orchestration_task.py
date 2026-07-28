# backend/tasks/orchestration_task.py
# Phase 2: Background orchestration via Celery
# Runs the full CEO → agents pipeline asynchronously
# Job status tracked in DB; results retrievable via GET /jobs/{job_id}
# Gracefully handles missing Celery/Redis

import asyncio, json, time, logging
from backend.tasks.celery_app import celery_app, CELERY_AVAILABLE

logger = logging.getLogger("AI-Digital-Company")


def _make_task():
    """Create the Celery task only if Celery is available."""
    if not CELERY_AVAILABLE or celery_app is None:
        return None

    @celery_app.task(bind=True, name="orchestration_task")
    def run_orchestration(self, job_id: str, task: str, username: str):
        """
        Celery task: full AI orchestration pipeline.
        Runs asynchronously — client polls /jobs/{job_id} for result.
        """
        logger.info(f"Celery task started | job={job_id} | user={username}")
        try:
            result = asyncio.run(_async_pipeline(job_id, task, username))
            return result
        except Exception as e:
            logger.error(f"Celery task failed | job={job_id} | {e}")
            asyncio.run(_mark_failed(job_id, str(e)))
            raise

    return run_orchestration


run_orchestration = _make_task()


async def _async_pipeline(job_id: str, task: str, username: str) -> dict:
    """Full async orchestration pipeline — same as /start-company/ but backgrounded."""
    from backend.agents.ceo_agent import ceo_agent
    from backend.agents.agent_executor import execute_agents
    from backend.core.tracer import ExecutionTracer
    from backend.core.scaling_engine import autonomous_scale
    from backend.core.hierarchy import get_active_structure
    from backend.database.db import (
        init_db, save_record, save_execution_stat,
        save_audit_record, update_job, get_recent_history
    )

    await init_db()
    await update_job(job_id, "running")
    tracer = ExecutionTracer()
    tracer.start(task)
    t_start = time.time()

    ceo = await ceo_agent(task)
    short_term  = ceo.get("short_term_strategy", "Execute core development.")
    long_term   = ceo.get("long_term_vision",    "Build a scalable product.")
    ceo_depts   = ceo.get("departments",         ["backend", "frontend"])
    raw_llm     = ceo.get("_raw_llm_response",   "")
    extracted   = ceo.get("_extracted_json",      {})

    tracer.add_memory_injection(3)
    tracer.add_ceo_decision(short_term, long_term, ceo_depts)

    final_depts, was_scaled, scale_reason = autonomous_scale(task, ceo_depts)
    if was_scaled:
        tracer.add_scaling_decision(ceo_depts, final_depts, scale_reason)

    dept_output = await execute_agents(final_depts, task, ceo_strategy=short_term)
    total_dur   = round(time.time() - t_start, 2)

    success = sum(1 for v in dept_output.values() if v.get("status") == "success")
    failed  = sum(1 for v in dept_output.values() if v.get("status") == "failed")

    for name, data in dept_output.items():
        tracer.add_agent_result(name, data.get("status","unknown"), data.get("execution_time_seconds",0), data.get("confidence",0.0))
    tracer.finish(total_dur, success, failed)

    result = {
        "job_id": job_id,
        "task": task,
        "requested_by": username,
        "ceo_strategy": {"short_term_strategy": short_term, "long_term_vision": long_term},
        "selected_departments": final_depts,
        "autonomous_scaling": {"triggered": was_scaled, "reason": scale_reason if was_scaled else "No scaling required."},
        "execution_summary": {"total_agents": len(final_depts), "successful": success, "failed": failed, "total_duration_seconds": total_dur},
        "reporting_structure": get_active_structure(final_depts),
        "departments": dept_output,
        "execution_trace": tracer.get_trace()
    }

    result_json = json.dumps(result)
    await save_record(task, result_json)
    await save_execution_stat(task, len(final_depts), success, failed, total_dur)
    await save_audit_record(task, raw_llm, extracted, final_depts, tracer.get_trace())
    await update_job(job_id, "completed", result_json)

    logger.info(f"Celery task done | job={job_id} | {total_dur}s")
    return result


async def _mark_failed(job_id: str, error: str):
    from backend.database.db import init_db, update_job
    await init_db()
    await update_job(job_id, "failed", error=error)
