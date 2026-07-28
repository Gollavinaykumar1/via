# backend/database/db.py — Phase 6: PostgreSQL + aiosqlite fallback
# Tries asyncpg (PostgreSQL) first; falls back to aiosqlite if PG is unreachable.

import json
import os
import aiosqlite
from backend.core.config import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
from backend.core.logger import logger

_pool = None
_sqlite_path = None
_using_sqlite = False


async def get_pool():
    global _pool
    if _pool is None:
        raise RuntimeError("DB pool not initialized.")
    return _pool


async def init_db():
    global _pool, _sqlite_path, _using_sqlite

    # Try PostgreSQL first
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(
            host=POSTGRES_HOST, port=POSTGRES_PORT, database=POSTGRES_DB,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD,
            min_size=2, max_size=10, command_timeout=60
        )
        _using_sqlite = False
        logger.info("PostgreSQL pool initialized.")
        await _create_tables_pg()
        return
    except Exception as e:
        logger.warning(f"PostgreSQL unavailable ({e}). Falling back to SQLite.")

    # Fallback: SQLite
    _sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "via_local.db")
    _using_sqlite = True
    _pool = True  # sentinel so get_pool() doesn't crash
    logger.info(f"Using SQLite at {_sqlite_path}")
    await _create_tables_sqlite()


async def close_db():
    global _pool, _using_sqlite
    if _pool and not _using_sqlite:
        try:
            await _pool.close()
            logger.info("DB pool closed.")
        except Exception:
            pass


# ─── Helper: get a sqlite connection ──────────────────────────────────────────

async def _sq():
    """Get an aiosqlite connection."""
    return await aiosqlite.connect(_sqlite_path)


# ─── Table Creation ───────────────────────────────────────────────────────────

async def _create_tables_pg():
    pool = await get_pool()
    async with pool.acquire() as c:
        await c.execute("""CREATE TABLE IF NOT EXISTS company_history (
            id SERIAL PRIMARY KEY, task TEXT NOT NULL, result TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS execution_stats (
            id SERIAL PRIMARY KEY, task TEXT NOT NULL,
            total_agents INT NOT NULL, successful_agents INT NOT NULL,
            failed_agents INT NOT NULL, total_duration REAL NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS decision_audit (
            id SERIAL PRIMARY KEY, task TEXT NOT NULL,
            raw_llm_response TEXT, extracted_json TEXT,
            final_departments TEXT, execution_timeline TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS auth_codes (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL,
            code TEXT NOT NULL, code_type TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS async_jobs (
            id TEXT PRIMARY KEY, task TEXT NOT NULL, status TEXT NOT NULL,
            result TEXT, error TEXT, created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS agent_memory (
            id SERIAL PRIMARY KEY, agent_name TEXT NOT NULL, task TEXT NOT NULL,
            output_summary TEXT, confidence REAL DEFAULT 0.0,
            created_at TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS meetings (
            id SERIAL PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, task TEXT NOT NULL,
            transcript TEXT, message_count INT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW())""")
        await c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL,
            message TEXT NOT NULL, intent TEXT DEFAULT 'chat',
            created_at TIMESTAMPTZ DEFAULT NOW())""")
    logger.info("All PostgreSQL tables ready.")


async def _create_tables_sqlite():
    async with aiosqlite.connect(_sqlite_path) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS company_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, result TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS execution_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL,
            total_agents INTEGER NOT NULL, successful_agents INTEGER NOT NULL,
            failed_agents INTEGER NOT NULL, total_duration REAL NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS decision_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL,
            raw_llm_response TEXT, extracted_json TEXT,
            final_departments TEXT, execution_timeline TEXT,
            timestamp TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL, is_active INTEGER DEFAULT 1,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS auth_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
            code TEXT NOT NULL, code_type TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS async_jobs (
            id TEXT PRIMARY KEY, task TEXT NOT NULL, status TEXT NOT NULL,
            result TEXT, error TEXT, created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT NOT NULL, task TEXT NOT NULL,
            output_summary TEXT, confidence REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT UNIQUE NOT NULL, task TEXT NOT NULL,
            transcript TEXT, message_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, role TEXT NOT NULL,
            message TEXT NOT NULL, intent TEXT DEFAULT 'chat',
            created_at TEXT DEFAULT (datetime('now')))""")
        await db.commit()
    logger.info("All SQLite tables ready.")


# ─── Core DB Operations ──────────────────────────────────────────────────────

async def save_record(task, result):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            cursor = await db.execute("INSERT INTO company_history (task, result) VALUES (?, ?)", (task, result))
            await db.commit()
            return cursor.lastrowid
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow("INSERT INTO company_history (task, result) VALUES ($1, $2) RETURNING id", task, result)
            return row["id"] if row else None


async def save_execution_stat(task, total, success, failed, duration):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                "INSERT INTO execution_stats (task, total_agents, successful_agents, failed_agents, total_duration) VALUES (?,?,?,?,?)",
                (task, total, success, failed, duration))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "INSERT INTO execution_stats (task, total_agents, successful_agents, failed_agents, total_duration) VALUES ($1,$2,$3,$4,$5)",
                task, total, success, failed, duration)


async def save_audit_record(task, raw_llm, extracted, departments, timeline):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                "INSERT INTO decision_audit (task, raw_llm_response, extracted_json, final_departments, execution_timeline) VALUES (?,?,?,?,?)",
                (task, raw_llm, json.dumps(extracted), json.dumps(departments), json.dumps(timeline)))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "INSERT INTO decision_audit (task, raw_llm_response, extracted_json, final_departments, execution_timeline) VALUES ($1,$2,$3,$4,$5)",
                task, raw_llm, json.dumps(extracted), json.dumps(departments), json.dumps(timeline))


async def get_recent_history(limit=10):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, task, result, timestamp FROM company_history ORDER BY id DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
        return [{"id": r["id"], "task": r["task"], "result": json.loads(r["result"]) if r["result"] else {}, "timestamp": str(r["timestamp"])} for r in rows]
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT id, task, result, timestamp FROM company_history ORDER BY id DESC LIMIT $1", limit)
        return [{"id": r["id"], "task": r["task"], "result": json.loads(r["result"]) if r["result"] else {}, "timestamp": str(r["timestamp"])} for r in rows]


async def get_history_by_id(project_id: int):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, task, result, timestamp FROM company_history WHERE id = ?", (project_id,))
            r = await cursor.fetchone()
            if r:
                return {"id": r["id"], "task": r["task"], "result": json.loads(r["result"]) if r["result"] else {}, "timestamp": str(r["timestamp"])}
            return None
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            r = await c.fetchrow("SELECT id, task, result, timestamp FROM company_history WHERE id = $1", project_id)
            if r:
                return {"id": r["id"], "task": r["task"], "result": json.loads(r["result"]) if r["result"] else {}, "timestamp": str(r["timestamp"])}
            return None


async def get_system_health():
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            cursor = await db.execute("""SELECT COUNT(*) AS runs, COALESCE(SUM(total_agents),0) AS ta,
                COALESCE(SUM(successful_agents),0) AS ts, COALESCE(SUM(failed_agents),0) AS tf,
                COALESCE(AVG(total_duration),0) AS avg_d, COALESCE(MAX(total_duration),0) AS max_d,
                COALESCE(MIN(total_duration),0) AS min_d FROM execution_stats""")
            r = await cursor.fetchone()
        ta = r[1] or 0; tf = r[3] or 0
        return {
            "total_runs": r[0], "total_agents_executed": ta,
            "total_successful": r[2], "total_failed": tf,
            "failure_rate_percent": round(tf/ta*100, 2) if ta else 0.0,
            "avg_duration_seconds": round(float(r[4] or 0), 2),
            "max_duration_seconds": round(float(r[5] or 0), 2),
            "min_duration_seconds": round(float(r[6] or 0), 2)
        }
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow("""SELECT COUNT(*) AS runs, COALESCE(SUM(total_agents),0) AS ta,
                COALESCE(SUM(successful_agents),0) AS ts, COALESCE(SUM(failed_agents),0) AS tf,
                COALESCE(AVG(total_duration),0) AS avg_d, COALESCE(MAX(total_duration),0) AS max_d,
                COALESCE(MIN(total_duration),0) AS min_d FROM execution_stats""")
        ta = row["ta"] or 0; tf = row["tf"] or 0
        return {
            "total_runs": row["runs"], "total_agents_executed": ta,
            "total_successful": row["ts"], "total_failed": tf,
            "failure_rate_percent": round(tf/ta*100, 2) if ta else 0.0,
            "avg_duration_seconds": round(float(row["avg_d"]), 2),
            "max_duration_seconds": round(float(row["max_d"]), 2),
            "min_duration_seconds": round(float(row["min_d"]), 2)
        }


async def get_company_status():
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            cursor = await db.execute("""SELECT COUNT(*) AS runs, COALESCE(AVG(total_duration),0) AS avg_d,
                COALESCE(CAST(SUM(failed_agents) AS FLOAT)/MAX(SUM(total_agents),1),0) AS fail_ratio
                FROM execution_stats""")
            stats = await cursor.fetchone()
            cursor2 = await db.execute("SELECT result FROM company_history ORDER BY id DESC LIMIT 50")
            rows = await cursor2.fetchall()
        dept_counts = {}
        for row in rows:
            try:
                res = json.loads(row[0])
                for d in res.get("selected_departments", []):
                    dept_counts[d] = dept_counts.get(d, 0) + 1
            except Exception: pass
        most_active = max(dept_counts, key=dept_counts.get) if dept_counts else "N/A"
        return {
            "total_executions": stats[0],
            "failure_rate_percent": round((stats[2] or 0)*100, 2),
            "average_response_time_seconds": round(float(stats[1] or 0), 2),
            "most_active_department": most_active,
            "department_activity": dept_counts
        }
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            stats = await c.fetchrow("""SELECT COUNT(*) AS runs, COALESCE(AVG(total_duration),0) AS avg_d,
                COALESCE(CAST(SUM(failed_agents) AS FLOAT)/NULLIF(SUM(total_agents),0),0) AS fail_ratio
                FROM execution_stats""")
            rows = await c.fetch("SELECT result FROM company_history ORDER BY id DESC LIMIT 50")
        dept_counts = {}
        for row in rows:
            try:
                res = json.loads(row["result"])
                for d in res.get("selected_departments", []):
                    dept_counts[d] = dept_counts.get(d, 0) + 1
            except Exception: pass
        most_active = max(dept_counts, key=dept_counts.get) if dept_counts else "N/A"
        return {
            "total_executions": stats["runs"],
            "failure_rate_percent": round((stats["fail_ratio"] or 0)*100, 2),
            "average_response_time_seconds": round(float(stats["avg_d"]), 2),
            "most_active_department": most_active,
            "department_activity": dept_counts
        }


# ─── Async Jobs ───────────────────────────────────────────────────────────────

async def create_job(job_id: str, task: str):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("INSERT INTO async_jobs (id, task, status) VALUES (?,?,'pending')", (job_id, task))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("INSERT INTO async_jobs (id, task, status) VALUES ($1,$2,'pending')", job_id, task)


async def update_job(job_id: str, status: str, result: str = None, error: str = None):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                "UPDATE async_jobs SET status=?, result=?, error=?, updated_at=datetime('now') WHERE id=?",
                (status, result, error, job_id))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "UPDATE async_jobs SET status=$1, result=$2, error=$3, updated_at=NOW() WHERE id=$4",
                status, result, error, job_id)


async def get_job(job_id: str):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, task, status, result, error, created_at, updated_at FROM async_jobs WHERE id=?", (job_id,))
            row = await cursor.fetchone()
        if not row: return None
        res = dict(row)
        if res.get("result"):
            try: res["result"] = json.loads(res["result"])
            except Exception: pass
        res["created_at"] = str(res["created_at"])
        res["updated_at"] = str(res["updated_at"])
        return res
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow("SELECT id, task, status, result, error, created_at, updated_at FROM async_jobs WHERE id=$1", job_id)
        if not row: return None
        res = dict(row)
        if res.get("result"):
            try: res["result"] = json.loads(res["result"])
            except Exception: pass
        res["created_at"] = str(res["created_at"])
        res["updated_at"] = str(res["updated_at"])
        return res


# ─── User Operations ─────────────────────────────────────────────────────────

async def get_user_by_email(email):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, email, hashed_password, is_active, is_verified FROM users WHERE email=?", (email,))
            row = await cursor.fetchone()
        return dict(row) if row else None
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow("SELECT id, email, hashed_password, is_active, is_verified FROM users WHERE email=$1", email)
        return dict(row) if row else None


# Keep old function name as alias so existing code doesn't break
async def get_user_by_username(username):
    return await get_user_by_email(username)


async def create_user(email, hashed_password):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("INSERT INTO users (email, hashed_password) VALUES (?,?)", (email, hashed_password))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("INSERT INTO users (email, hashed_password) VALUES ($1,$2)", email, hashed_password)


async def verify_user_email(email):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("UPDATE users SET is_verified=1 WHERE email=?", (email,))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("UPDATE users SET is_verified=TRUE WHERE email=$1", email)


async def update_user_password(email, hashed_password):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("UPDATE users SET hashed_password=? WHERE email=?", (hashed_password, email))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("UPDATE users SET hashed_password=$1 WHERE email=$2", hashed_password, email)


async def save_auth_code(email, code, code_type, expires_at):
    """Save a verification or reset code to the database."""
    from datetime import datetime as _dt
    # Normalize expires_at to datetime object for PG compatibility
    if isinstance(expires_at, str):
        try:
            expires_dt = _dt.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        except Exception:
            expires_dt = expires_at
    else:
        expires_dt = expires_at

    # Clear old codes of this type first
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("DELETE FROM auth_codes WHERE email=? AND code_type=?", (email, code_type))
            await db.execute("INSERT INTO auth_codes (email, code, code_type, expires_at) VALUES (?,?,?,?)",
                             (email, code, code_type, expires_at))  # SQLite takes string fine
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("DELETE FROM auth_codes WHERE email=$1 AND code_type=$2", email, code_type)
            await c.execute("INSERT INTO auth_codes (email, code, code_type, expires_at) VALUES ($1,$2,$3,$4)",
                            email, code, code_type, expires_dt)  # PG needs datetime object


async def get_auth_code(email, code, code_type):
    """Get a valid (non-expired) auth code for an email."""
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, email, code, code_type, expires_at FROM auth_codes WHERE email=? AND code=? AND code_type=? AND expires_at > datetime('now')",
                (email, code, code_type))
            row = await cursor.fetchone()
        return dict(row) if row else None
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT id, email, code, code_type, expires_at FROM auth_codes WHERE email=$1 AND code=$2 AND code_type=$3 AND expires_at > NOW()",
                email, code, code_type)
        return dict(row) if row else None


async def delete_auth_code(email, code_type):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("DELETE FROM auth_codes WHERE email=? AND code_type=?", (email, code_type))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("DELETE FROM auth_codes WHERE email=$1 AND code_type=$2", email, code_type)


# ─── Agent Memory ─────────────────────────────────────────────────────────────

async def save_agent_mem(agent: str, task: str, output_summary: str, confidence: float):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                "INSERT INTO agent_memory (agent_name, task, output_summary, confidence) VALUES (?,?,?,?)",
                (agent, task, output_summary, confidence))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "INSERT INTO agent_memory (agent_name, task, output_summary, confidence) VALUES ($1,$2,$3,$4)",
                agent, task, output_summary, confidence)


async def get_agent_mem(agent: str, limit: int = 5):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT task, output_summary, confidence, created_at FROM agent_memory WHERE agent_name=? ORDER BY id DESC LIMIT ?",
                (agent, limit))
            return await cursor.fetchall()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            return await c.fetch(
                "SELECT task, output_summary, confidence, created_at FROM agent_memory WHERE agent_name=$1 ORDER BY id DESC LIMIT $2",
                agent, limit)


async def get_all_mem(limit: int = 50):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT agent_name, task, output_summary, confidence, created_at FROM agent_memory ORDER BY id DESC LIMIT ?",
                (limit,))
            return await cursor.fetchall()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            return await c.fetch(
                "SELECT agent_name, task, output_summary, confidence, created_at FROM agent_memory ORDER BY id DESC LIMIT $1",
                limit)


async def get_agent_memory_for_task_db(agent: str, task: str):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT output_summary, confidence, created_at FROM agent_memory WHERE agent_name=? AND task=? ORDER BY id DESC LIMIT 1",
                (agent, task))
            return await cursor.fetchone()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            return await c.fetchrow(
                "SELECT output_summary, confidence, created_at FROM agent_memory WHERE agent_name=$1 AND task=$2 ORDER BY id DESC LIMIT 1",
                agent, task)


# ─── Meetings ─────────────────────────────────────────────────────────────────

async def save_meeting_db(job_id: str, task: str, transcript: str, message_count: int):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                """INSERT INTO meetings (job_id, task, transcript, message_count) VALUES (?,?,?,?)
                   ON CONFLICT(job_id) DO UPDATE SET transcript=excluded.transcript, message_count=excluded.message_count""",
                (job_id, task, transcript, message_count))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                """INSERT INTO meetings (job_id, task, transcript, message_count)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (job_id) DO UPDATE
                   SET transcript=$3, message_count=$4""",
                job_id, task, transcript, message_count)


async def get_meeting_db(job_id: str):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT job_id, task, transcript, message_count, created_at FROM meetings WHERE job_id=?",
                (job_id,))
            row = await cursor.fetchone()
        return dict(row) if row else None
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT job_id, task, transcript, message_count, created_at FROM meetings WHERE job_id=$1",
                job_id)
        return dict(row) if row else None


async def get_recent_meetings_db(limit: int = 10):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT job_id, task, message_count, created_at FROM meetings ORDER BY id DESC LIMIT ?",
                (limit,))
            return await cursor.fetchall()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            return await c.fetch(
                "SELECT job_id, task, message_count, created_at FROM meetings ORDER BY id DESC LIMIT $1",
                limit)


# ─── Chat History ─────────────────────────────────────────────────────────────

async def save_chat_message(username: str, role: str, message: str, intent: str = "chat"):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(
                "INSERT INTO chat_history (username, role, message, intent) VALUES (?,?,?,?)",
                (username, role, message, intent))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "INSERT INTO chat_history (username, role, message, intent) VALUES ($1,$2,$3,$4)",
                username, role, message, intent)


async def get_chat_history(username: str, limit: int = 50):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, message, intent, created_at FROM chat_history WHERE username=? ORDER BY id DESC LIMIT ?",
                (username, limit))
            rows = await cursor.fetchall()
        return [
            {"role": r["role"], "message": r["message"], "intent": r["intent"],
             "timestamp": str(r["created_at"])}
            for r in reversed(rows or [])
        ]
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            rows = await c.fetch(
                "SELECT role, message, intent, created_at FROM chat_history WHERE username=$1 ORDER BY id DESC LIMIT $2",
                username, limit)
        return [
            {"role": r["role"], "message": r["message"], "intent": r["intent"],
             "timestamp": str(r["created_at"])}
            for r in reversed(rows or [])
        ]


async def clear_chat_history(username: str):
    if _using_sqlite:
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("DELETE FROM chat_history WHERE username=?", (username,))
            await db.commit()
    else:
        pool = await get_pool()
        async with pool.acquire() as c:
            await c.execute("DELETE FROM chat_history WHERE username=$1", username)