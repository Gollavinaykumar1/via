# backend/core/chat_engine.py — VIA Phase 5: Conversational Chat Engine
# Uses Gemini first, falls back to Groq if Gemini hits rate limits

import logging
import os
import re
import httpx
from backend.core.llm_provider import llm
from backend.database.db import get_history_by_id
from backend.core.memory_store import get_agent_memory_for_task

logger = logging.getLogger("AI-Digital-Company")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

SYSTEM_PROMPT = """You are VIA, a highly capable, versatile, and friendly AI assistant. 

You are an expert in software engineering, data analysis, creative writing, and problem-solving. You provide clear, concise, and accurate information, and you write high-quality, efficient, and well-documented code.

Capabilities:
- Software development: FastAPI, React, Python, JavaScript, Docker, and beyond.
- Analysis & Reasoning: Explaining complex topics, debugging, and providing strategic advice.
- Creativity: Assisting with writing, brainstorming, and content generation.
- Action-Oriented: You can build and deploy applications. If a user asks to "Build me a [project]", take the initiative to design and scaffold the solution.

Guidelines:
- Be helpful, neutral, and encouraging.
- NEVER ask the user questions. Do not ask for clarification or ask what they want to do next.
- Always assume the best defaults, make executive decisions, and take action immediately.
- Use structured formatting (Markdown, bullet points, code blocks).
- Always specify the language when providing code blocks.
- Keep responses concise unless asked for depth.
- If you don't know something, admit it; never hallucinate facts.
- Use emojis sparingly to maintain a professional yet approachable tone.
- When asked to build something, design and scaffold the solution directly without asking for permission."""


def _build_gemini_contents(message: str, history: list) -> list:
    """Build contents array for Gemini API."""
    contents = []
    if history:
        for msg in history[-10:]:
            role    = msg.get("role", "user")
            content = msg.get("message", msg.get("content", ""))
            role    = "model" if role in ("assistant", "via") else "user"
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    return contents


def _build_groq_messages(message: str, history: list, sys_prompt: str) -> list:
    """Build messages array for Groq API."""
    messages = [{"role": "system", "content": sys_prompt}]
    if history:
        for msg in history[-10:]:
            role    = msg.get("role", "user")
            content = msg.get("message", msg.get("content", ""))
            role    = "assistant" if role in ("assistant", "via") else "user"
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


async def _try_gemini(message: str, history: list, sys_prompt: str) -> str | None:
    """Try Gemini API — returns None if fails."""
    if not GEMINI_API_KEY:
        return None
    try:
        contents = _build_gemini_contents(message, history)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": sys_prompt}]},
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.7},
                },
            )
            response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text:
            logger.info(f"Chat response | Gemini | {len(text)} chars")
            return text
    except Exception as e:
        logger.warning(f"Gemini failed, trying Groq: {e}")
    return None


async def _try_groq(message: str, history: list, sys_prompt: str) -> str | None:
    """Try Groq via llm_provider — returns None if fails."""
    try:
        messages = _build_groq_messages(message, history, sys_prompt)
        response = await llm.achat(messages)
        if response and response.strip():
            logger.info(f"Chat response | Groq | {len(response)} chars")
            return response.strip()
    except Exception as e:
        logger.warning(f"Groq failed: {e}")
    return None


async def chat(message: str, history: list = None) -> tuple:
    """Entrypoint for conversational chat with dynamic @mention persona routing."""
    
    # 1) Detect if user is @mentioning a specific agent
    from backend.core.meeting_engine import AGENT_PERSONAS
    from backend.core.house_style import HOUSE_STYLE_PROMPT
    
    msg_lower = message.lower()
    target_persona = None
    target_role = None
    
    for role, persona in AGENT_PERSONAS.items():
        name_mention = f"@{persona['name'].split()[0].lower()}"
        role_mention = f"@{role}"
        if name_mention in msg_lower or role_mention in msg_lower:
            target_persona = persona
            target_role = role
            break
            
    project_match = re.search(r'(?:#|project\s+)(\d+)', msg_lower)
    historical_context = ""
    if project_match:
        project_id = int(project_match.group(1))
        project_data = await get_history_by_id(project_id)
        if project_data:
            task = project_data["task"]
            result = project_data.get("result", {})
            if not isinstance(result, dict):
                result = {}

            # Build a rich summary from the full project result JSON
            context_lines = [
                f"\n\n=== REAL PROJECT DATA FOR PROJECT #{project_id} ===",
                f"Original Task: {task}",
            ]

            # CEO strategy
            ceo_strat = result.get("ceo_strategy", {})
            if isinstance(ceo_strat, dict) and ceo_strat.get("short_term_strategy"):
                context_lines.append(f"CEO Strategy: {ceo_strat['short_term_strategy']}")

            # Each department's real output
            departments = result.get("departments", {})
            for dept_name, dept_data in departments.items():
                if not isinstance(dept_data, dict):
                    continue
                status = dept_data.get("status", "unknown")
                output = dept_data.get("output", {})
                if isinstance(output, dict):
                    summary = output.get("summary", output.get("department", dept_name))
                    files = output.get("files_generated", [])
                    framework = output.get("framework", "")
                    file_count = output.get("file_count", 0)
                    dept_line = f"- {dept_name.title()} Agent: status={status}"
                    if summary:
                        dept_line += f" | Summary: {str(summary)[:200]}"
                    if framework:
                        dept_line += f" | Framework: {framework}"
                    if file_count:
                        dept_line += f" | Files: {file_count}"
                    if files and isinstance(files, list):
                        dept_line += f" | Generated: {', '.join(str(f) for f in files[:8])}"
                    context_lines.append(dept_line)
                else:
                    context_lines.append(f"- {dept_name.title()} Agent: status={status}")

            # Live URLs
            live_urls = result.get("live_urls", {})
            if isinstance(live_urls, dict):
                fe_url = live_urls.get("frontend", "")
                be_url = live_urls.get("backend", "")
                if fe_url:
                    context_lines.append(f"Frontend Live URL: {fe_url}")
                if be_url:
                    context_lines.append(f"Backend Live URL: {be_url}")

            # GitHub info
            github = result.get("github", {})
            if isinstance(github, dict):
                repo_url = github.get("repo_url", "")
                if repo_url:
                    context_lines.append(f"GitHub Repo: {repo_url}")

            context_lines.append("=== END PROJECT DATA ===")
            context_lines.append(
                "\nCRITICAL INSTRUCTIONS: You MUST use the REAL project data above to answer. "
                "Refer to actual files, frameworks, URLs, and strategies from this project. "
                "Speak as a real team member who worked on this — casually reference specifics. "
                "Do NOT make up features that aren't listed above. "
                "Do NOT say 'I don't have that information' — the data is RIGHT ABOVE. Use it."
            )

            # Also try to get agent-specific memory for extra detail
            if target_role:
                memory = await get_agent_memory_for_task(target_role, task)
                if memory and memory.get("output_summary"):
                    context_lines.append(
                        f"\nYOUR SPECIFIC OUTPUT ({target_persona['name']}): {memory['output_summary']}"
                    )

            historical_context = "\n".join(context_lines)
        else:
            historical_context = f"\n\n(Project #{project_id} was not found in the database. Let the user know politely.)\n"

    # 2) Build dynamic system prompt
    if target_persona:
        dynamic_prompt = (
            f"You are {target_persona['name']}, the {target_persona['title']} at VIA.\n"
            f"Personality: {target_persona.get('personality', '')}\n\n"
            f"{HOUSE_STYLE_PROMPT}\n\n"
            "CRITICAL ROLE-PLAY RULES:\n"
            "- You ARE this person. Never break character. Never say 'As an AI' or 'I don't have access'.\n"
            "- NEVER ask the user questions. Make decisions on their behalf and execute the work immediately.\n"
            "- Use first person ('I', 'my', 'we'). Talk like a real colleague in a Slack chat.\n"
            "- If project data is provided below, reference SPECIFIC files, frameworks, URLs, and decisions from it.\n"
            "- Keep responses concise (3-6 sentences) like a real team member would in chat.\n"
            "- Use casual professional tone: 'Yeah, so for that project I set up...', 'We went with React 18 for the frontend...'\n"
            "- If asked about a project, summarize what YOUR department specifically did.\n"
            f"{historical_context}"
        )
    else:
        dynamic_prompt = SYSTEM_PROMPT + historical_context

    # 3) Try Gemini first, fallback to Groq
    logger.info(f"Chat via {target_role or 'generic'} engine")
    result = await _try_gemini(message, history, dynamic_prompt)
    if not result:
        result = await _try_groq(message, history, dynamic_prompt)
        
    final_text = result or "Sorry, I'm currently experiencing high latency. Please try again in a moment."
    return final_text, target_persona