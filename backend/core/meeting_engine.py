# backend/core/meeting_engine.py — VIA Phase 3: Agent Meeting Room

import asyncio
import time
import logging
from backend.core.llm_provider import llm

logger = logging.getLogger("AI-Digital-Company")

AGENT_PERSONAS = {
    "ceo": {
        "name": "Vinay",
        "title": "CEO & Visionary",
        "emoji": "👔",
        "personality": "Strategic, decisive, inspiring. Speaks in big-picture terms. Uses phrases like 'This aligns with our vision', 'Let's move fast on this', 'What's the bottleneck?'",
        "color": "m2"
    },
    "backend": {
        "name": "Sravanthi",
        "title": "Backend Architect",
        "emoji": "⚙️",
        "personality": "Technical, precise, pragmatic. Talks about APIs, databases, performance. Uses phrases like 'We need to consider scalability', 'The API contract should be', 'I'll wire up the endpoints'",
        "color": "c"
    },
    "frontend": {
        "name": "Rajesh",
        "title": "Senior Frontend Engineer",
        "emoji": "🎨",
        "personality": "Creative, user-focused, detail-oriented. Talks about UX, components, responsiveness. Uses phrases like 'The user journey needs to', 'I'll build a clean interface', 'Let me sketch the component tree'",
        "color": "v2"
    },
    "security": {
        "name": "Ramesh",
        "title": "Security Architect",
        "emoji": "🔐",
        "personality": "Cautious, thorough, risk-aware. Always thinking about threats. Uses phrases like 'We need to threat model this', 'Authentication must be', 'What about injection attacks?'",
        "color": "y"
    },
    "devops": {
        "name": "Suresh",
        "title": "DevOps Lead",
        "emoji": "🚀",
        "personality": "Practical, efficiency-driven, automation-obsessed. Uses phrases like 'I'll set up the CI/CD pipeline', 'Container this with Docker', 'Zero-downtime deployment is critical'",
        "color": "g"
    },
    "ai_research": {
        "name": "RDX",
        "title": "AI Research Director",
        "emoji": "🧠",
        "personality": "Analytical, curious, forward-thinking. Talks about models, data, ML pipelines. Uses phrases like 'The model architecture should', 'Training data quality matters', 'Let me run some benchmarks'",
        "color": "v"
    },
    "architecture": {
        "name": "Chandra",
        "title": "Solutions Architect",
        "emoji": "📐",
        "personality": "Systematic, design-focused, pattern-aware. Talks about system design and scalability. Uses phrases like 'The microservices boundary should be', 'Event-driven architecture fits here', 'Let me draw the data flow'",
        "color": "o"
    },
    "hr": {
        "name": "Lakshmi Kanth",
        "title": "HR Director",
        "emoji": "👥",
        "personality": "Empathetic, people-focused, organized. Talks about team dynamics and culture. Uses phrases like 'We need to hire for this gap', 'Team morale is critical', 'Let me draft the onboarding plan'",
        "color": "m"
    },
    "finance": {
        "name": "Satvik",
        "title": "CFO",
        "emoji": "💰",
        "personality": "Numbers-driven, risk-conscious, ROI-focused. Uses phrases like 'What's the burn rate?', 'We need to optimize costs', 'The break-even point is'",
        "color": "g2"
    },
    "marketing": {
        "name": "Sweety",
        "title": "CMO",
        "emoji": "📣",
        "personality": "Creative, data-driven, growth-obsessed. Talks about positioning, GTM, growth channels. Uses phrases like 'This is our differentiator', 'Target persona is', 'I see a viral loop here'",
        "color": "c2"
    },
}


async def _build_meeting_historical_context(task_query: str, departments: list) -> str:
    import re
    from backend.database.db import get_history_by_id
    from backend.core.memory_store import get_agent_memory_for_task

    match = re.search(r'(?:#|project\s+)(\d+)', task_query.lower())
    if not match:
        return ""

    project_id = int(match.group(1))
    project_data = await get_history_by_id(project_id)
    if not project_data:
        return f"\n(No database record found for Project #{project_id})\n"

    orig_task = project_data.get("task", "")
    context = f"\n=== REAL HISTORICAL DATA FOR PROJECT #{project_id} ===\n"
    context += f"Original Project Task: {orig_task}\n"
    context += "Here is exactly what the agents completed for this project:\n"

    for dept in departments:
        if dept == "ceo":
            strategy_obj = project_data.get("result", {})
            if isinstance(strategy_obj, dict):
                short_term = strategy_obj.get("ceo_strategy", {}).get("short_term_strategy", "Standard execution.")
            else:
                short_term = "Standard execution."
            context += f"- CEO (Alex Chen) Strategy: {short_term}\n"
        else:
            mem = await get_agent_memory_for_task(dept, orig_task)
            summary = mem.get("output_summary") if mem else None
            if summary:
                context += f"- {dept.title()} Agent ({AGENT_PERSONAS.get(dept, {}).get('name', dept)}): {summary}\n"
            else:
                context += f"- {dept.title()} Agent ({AGENT_PERSONAS.get(dept, {}).get('name', dept)}): No memory details available.\n"
    context += "=================================================\n"
    context += "CRITICAL: You MUST write the meeting dialogue based strictly on the REAL historical details listed above. All agents must speak about what they actually built/did in that project. Do not make up mock files or general templates. Speak naturally, referencing their real files and choices from this project."
    return context


async def generate_meeting(task: str, departments: list, ceo_strategy: str) -> list:
    """
    Generate a realistic agent meeting transcript.
    Returns list of message dicts: {agent, name, emoji, message, timestamp, color}
    """
    messages = []
    t = time.time()

    def msg(agent_key: str, text: str):
        persona = AGENT_PERSONAS.get(agent_key, AGENT_PERSONAS["ceo"])
        messages.append({
            "agent": agent_key,
            "name": persona["name"],
            "title": persona["title"],
            "emoji": persona["emoji"],
            "message": text,
            "timestamp": round(time.time() - t, 2),
            "color": persona["color"],
        })

    historical_context = await _build_meeting_historical_context(task, departments)

    # Phase 1: CEO opens the meeting
    prompt_ceo_open = f"""You are Alex Chen, CEO of VIA (an autonomous AI company).
You're opening a team meeting about this project: {task}

Strategy decided: {ceo_strategy}
{historical_context}

Write a brief (3-4 sentences) energetic CEO opening statement to kick off the meeting.
Be specific about the task, mention the strategy, and motivate the team.
No quotes, no labels, just the speech text directly."""

    ceo_opening = await llm.agenerate(prompt_ceo_open)
    msg("ceo", ceo_opening.strip() if ceo_opening else f"Team, we've just received a critical task: {task}. Our strategy is clear — {ceo_strategy}. Let's execute fast and smart. I need every department to align on their deliverables today.")

    # Phase 2: Departments respond
    active_depts = [d for d in departments if d in AGENT_PERSONAS and d != "ceo"]

    for dept in active_depts[:5]:  # Limit to 5 departments for concise meeting
        persona = AGENT_PERSONAS[dept]
        prompt_dept = f"""You are {persona['name']}, {persona['title']} at VIA.
Personality: {persona['personality']}

The CEO just opened a meeting about: {task}
CEO Strategy: {ceo_strategy}
{historical_context}

Write your department's response (2-3 sentences). What will YOUR team specifically do?
Mention your key action items or concerns.
No quotes, no labels, just speak naturally as {persona['name']}."""

        dept_response = await llm.agenerate(prompt_dept)
        if dept_response:
            msg(dept, dept_response.strip())

    # Phase 3: Cross-department interaction (security asks a question)
    if "security" in departments and "backend" in departments:
        prompt_security_q = f"""You are Zara Ahmed, Security Architect at VIA.
The backend team just said they'll build APIs for: {task}

Ask ONE sharp security question to the backend engineer about authentication or data protection.
Keep it to 1-2 sentences. Be direct and technical."""

        sec_q = await llm.agenerate(prompt_security_q)
        if sec_q:
            msg("security", sec_q.strip())

        # Backend responds to security
        prompt_backend_ans = f"""You are Priya Sharma, Lead Backend Engineer at VIA.
The security architect just raised a security concern about authentication for: {task}

Give a confident 1-2 sentence technical answer about how you'll handle security in the backend."""

        be_ans = await llm.agenerate(prompt_backend_ans)
        if be_ans:
            msg("backend", be_ans.strip())

    # Phase 4: CEO closes with action items
    dept_names = [AGENT_PERSONAS[d]["name"] for d in active_depts[:4]]
    prompt_ceo_close = f"""You are Alex Chen, CEO of VIA.
The team meeting about "{task}" is wrapping up.

Write a crisp 2-3 sentence closing statement that:
1. Assigns clear ownership (mention 1-2 team members by name: {', '.join(dept_names)})
2. Sets urgency / deadline
3. Motivates the team

No quotes, no labels, just the closing speech."""

    ceo_close = await llm.agenerate(prompt_ceo_close)
    msg("ceo", ceo_close.strip() if ceo_close else f"Excellent discussion everyone. {dept_names[0] if dept_names else 'Team'}, you have the backend. Let's ship this within the sprint — no excuses. VIA moves fast!")

    return messages


async def generate_meeting_fast(task: str, departments: list, ceo_strategy: str) -> list:
    """
    Faster version: generates a pre-scripted meeting without LLM calls for each message.
    Uses a single LLM call to generate the whole transcript.
    """
    dept_personas = []
    for d in departments:
        if d in AGENT_PERSONAS:
            p = AGENT_PERSONAS[d]
            dept_personas.append(f"- {p['name']} ({p['title']}): {p['personality'][:80]}")

    personas_text = "\n".join(dept_personas)

    historical_context = await _build_meeting_historical_context(task, departments)

    prompt = f"""You are writing a realistic team meeting transcript for VIA's autonomous AI company.

PROJECT: {task}
CEO STRATEGY: {ceo_strategy}
{historical_context}

TEAM MEMBERS:
{personas_text}

Write a natural meeting transcript with 8-12 exchanges. Format EXACTLY like this (one per line):
SPEAKER_KEY|Message text here

Valid speaker keys: ceo, backend, frontend, security, devops, ai_research, architecture, hr, finance, marketing

Rules:
- CEO opens and closes the meeting
- Each department mentions their specific deliverable
- Include 1-2 cross-department questions/debates
- Keep each message to 2-3 sentences max
- Make it sound like a real Slack/Teams standup
- Only use speaker keys from the Valid list above
"""

    try:
        raw = await llm.agenerate(prompt)
        messages = []
        t = time.time()

        if raw:
            for line in raw.strip().split("\n"):
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    if len(parts) == 2:
                        agent_key = parts[0].strip().lower()
                        text = parts[1].strip()
                        if agent_key in AGENT_PERSONAS and text:
                            persona = AGENT_PERSONAS[agent_key]
                            messages.append({
                                "agent": agent_key,
                                "name": persona["name"],
                                "title": persona["title"],
                                "emoji": persona["emoji"],
                                "message": text,
                                "timestamp": round(time.time() - t, 3),
                                "color": persona["color"],
                            })

        if not messages:
            # Fallback: simple scripted meeting
            messages = _scripted_fallback(task, departments, ceo_strategy)

        return messages

    except Exception as e:
        logger.error(f"Meeting generation failed: {e}")
        return _scripted_fallback(task, departments, ceo_strategy)


def _scripted_fallback(task: str, departments: list, ceo_strategy: str) -> list:
    """Pre-written fallback meeting if LLM fails."""
    t = time.time()
    messages = []

    def msg(agent_key, text):
        persona = AGENT_PERSONAS.get(agent_key, AGENT_PERSONAS["ceo"])
        messages.append({
            "agent": agent_key,
            "name": persona["name"],
            "title": persona["title"],
            "emoji": persona["emoji"],
            "message": text,
            "timestamp": round(time.time() - t, 3),
            "color": persona["color"],
        })

    msg("ceo", f"Team, we have a new priority: '{task[:100]}'. Strategy: {ceo_strategy[:120]}. Everyone align on your deliverables — we move today.")

    dept_msgs = {
        "backend": "I'll architect the FastAPI backend with PostgreSQL. Estimating 3 endpoints in the first sprint. Database schema will be ready by EOD.",
        "frontend": "I'll build the React UI with mobile-first design. Component library is already set up. We'll have a working prototype in 48 hours.",
        "security": "I need to threat-model this before we ship. JWT auth, input validation, and rate limiting are non-negotiable. I'll deliver the security spec today.",
        "devops": "CI/CD pipeline will be live by tomorrow. Docker containers, GitHub Actions, and Render deployment are all ready to configure.",
        "ai_research": "I'll evaluate which LLM fits this use case best. Fine-tuning vs. prompt engineering decision will be made after running benchmarks tonight.",
        "architecture": "System design doc is drafted. I'm recommending a microservices boundary between auth and core services. Review it before we start coding.",
        "hr": "I'll define the team roles and have job descriptions ready. Onboarding plan for any new hires follows next week.",
        "finance": "Initial budget estimate is being prepared. I'll have the ROI projection and cost breakdown in your inbox by 5 PM.",
        "marketing": "GTM strategy is already forming. I'm thinking Product Hunt launch + LinkedIn campaign. Personas and messaging framework by end of week.",
    }

    for dept in departments:
        if dept in dept_msgs and dept != "ceo":
            msg(dept, dept_msgs[dept])

    msg("ceo", "Outstanding. Everyone has clear ownership. Ship fast, ship clean. VIA doesn't miss deadlines — let's make history with this one.")

    return messages


async def run_pre_build_discussion(
    task: str,
    departments: list,
    ceo_strategy: str,
    ws_manager=None,
    job_id: str = None,
) -> list:
    """
    Run a structured agent discussion DURING build before final output.
    Agents share decisions that affect each other (API shape, security constraints, infra limits).
    CEO gets final say on conflicts.
    Returns list of exchange message dicts.
    """
    messages = []
    t = time.time()

    def _add(agent_key: str, text: str):
        persona = AGENT_PERSONAS.get(agent_key, AGENT_PERSONAS["ceo"])
        msg = {
            "agent": agent_key,
            "name": persona["name"],
            "title": persona["title"],
            "emoji": persona["emoji"],
            "message": text,
            "timestamp": round(time.time() - t, 3),
            "color": persona["color"],
            "type": "build_discussion",
        }
        messages.append(msg)
        return msg

    active = [d for d in departments if d in AGENT_PERSONAS and d != "ceo"]
    conflict_flagged = False

    # 1. Backend shares API shape with Frontend
    if "backend" in active and "frontend" in active:
        prompt = f"""You are Dev, Staff Backend Engineer at VIA. You're mid-build on: {task}

Tell the Frontend engineer the exact API shape they should expect:\n- The main API endpoint path and HTTP method\n- What the request body looks like (fields and types)\n- What the response JSON looks like\n- Any auth headers required\n\nKeep it to 3-4 sentences. Be specific and technical. No intros or sign-offs."""
        resp = await llm.agenerate(prompt)
        msg = _add("backend", resp.strip() if resp else "I'm setting up REST endpoints at /api/v1/ — you'll POST to create and GET to list. Auth via JWT Bearer header. Response is a list of items with id, name, created_at fields.")
        if ws_manager and job_id:
            await ws_manager.broadcast(job_id, "build_discussion", msg)

    # 2. Security flags a concern about what Backend proposed
    if "security" in active and "backend" in active:
        prompt = f"""You are Ravi, Head of Security at VIA. The backend team just described their API for: {task}\n\nYou've spotted a potential risk. Call it out directly in 2 sentences — be specific about what could go wrong and what the fix is. Don't sugarcoat it."""
        resp = await llm.agenerate(prompt)
        msg = _add("security", resp.strip() if resp else "I'm seeing a missing rate-limit on the auth endpoints — that's a brute-force vector. We need 5 req/min per IP before this ships.")
        if ws_manager and job_id:
            await ws_manager.broadcast(job_id, "build_discussion", msg)
        conflict_flagged = True

    # 3. Backend responds to Security concern
    if conflict_flagged and "backend" in active:
        prompt = f"""You are Dev, Staff Backend Engineer at VIA. Security just flagged a risk in your API for: {task}\n\nAcknowledge it and state what you'll change in your implementation. 2 sentences. Be direct."""
        resp = await llm.agenerate(prompt)
        msg = _add("backend", resp.strip() if resp else "Fair point — adding slowapi rate limiter at 5/min on /auth/ routes. Won't touch the rest of the stack.")
        if ws_manager and job_id:
            await ws_manager.broadcast(job_id, "build_discussion", msg)

    # 4. DevOps raises infra constraint
    if "devops" in active:
        prompt = f"""You are Sam, DevOps Lead at VIA. The team is building: {task}\n\nMention ONE infra or deployment constraint they need to be aware of while building. 2 sentences, calm, specific."""
        resp = await llm.agenerate(prompt)
        msg = _add("devops", resp.strip() if resp else "Heads up — Render free tier has a 512MB memory limit so keep the Docker image lean. Make sure DATABASE_URL is in env vars, not hardcoded.")
        if ws_manager and job_id:
            await ws_manager.broadcast(job_id, "build_discussion", msg)

    # 5. CEO closes with a decision if there was a conflict
    if conflict_flagged:
        dept_names = [AGENT_PERSONAS[d]["name"] for d in active[:3] if d in AGENT_PERSONAS]
        prompt = f"""You are Arjun, CEO of VIA. Your team just had a quick discussion about a security concern during the build of: {task}\n\nClose this out in 2 sentences. Assign the fix to the right person (use their name from: {', '.join(dept_names)}) and confirm we're moving forward. Be decisive."""
        resp = await llm.agenerate(prompt)
        msg = _add("ceo", resp.strip() if resp else f"Good catch — get that rate limiter in before push. We're not shipping a security hole. Move.")
        if ws_manager and job_id:
            await ws_manager.broadcast(job_id, "build_discussion", msg)

    return messages
