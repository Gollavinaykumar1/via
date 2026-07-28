# backend/core/llm_provider.py — Groq + Gemini + Ollama support
# Strategy: Groq for all planning/logic agents (fast, 30 RPM free)
#           Gemini for frontend agent only (quality UI code)
import asyncio, requests, time, os
from .config import MODEL_NAME, OLLAMA_URL, REQUEST_TIMEOUT, LLM_MAX_RETRIES, LLM_RETRY_DELAY
from .logger import logger

USE_GROQ      = os.getenv("USE_GROQ", "false").lower() == "true"
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MAX_TOK  = int(os.getenv("GROQ_MAX_TOKENS", "4000"))
GROQ_TEMP     = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"

USE_ANTHROPIC     = os.getenv("USE_ANTHROPIC", "false").strip().lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620").strip()
ANTHROPIC_URL     = "https://api.anthropic.com/v1/messages"

USE_GEMINI        = os.getenv("USE_GEMINI", "false").strip().lower() == "true"
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
GEMINI_URL        = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

import itertools
_groq_keys = [v for k, v in os.environ.items() if k.startswith("GROQ_API_KEY") and v.strip()]
if not _groq_keys and GROQ_API_KEY:
    _groq_keys = [GROQ_API_KEY]
if not _groq_keys:
    _groq_keys = [""]
key_iterator = itertools.cycle(_groq_keys)


class LLMProvider:
    def __init__(self):
        self.model       = MODEL_NAME
        self.url         = OLLAMA_URL
        self.timeout     = REQUEST_TIMEOUT
        self.max_retries = LLM_MAX_RETRIES
        self.retry_delay = LLM_RETRY_DELAY
        self.use_groq    = USE_GROQ
        self.use_anthropic = USE_ANTHROPIC
        self.use_gemini  = USE_GEMINI

        if self.use_gemini:
            logger.info(f"LLM Provider | Gemini | model={GEMINI_MODEL}")
        elif self.use_anthropic:
            logger.info(f"LLM Provider | Anthropic | model={ANTHROPIC_MODEL}")
        elif self.use_groq:
            logger.info(f"LLM Provider | Groq | model={GROQ_MODEL}")
        else:
            logger.info(f"LLM Provider | Ollama | model={self.model}")

    def _generate_groq(self, prompt: str) -> str:
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                current_key = next(key_iterator)
                r = requests.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {current_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       GROQ_MODEL,
                        "messages":    [{"role": "user", "content": prompt}],
                        "max_tokens":  GROQ_MAX_TOK,
                        "temperature": GROQ_TEMP,
                    },
                    timeout=60,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM ok | Groq | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Groq error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                        delay = max(delay, 5) # Minimum 5s backoff for 429
                    time.sleep(delay)
        return ""

    def _generate_ollama(self, prompt: str) -> str:
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                r = requests.post(
                    self.url,
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=self.timeout,
                )
                r.raise_for_status()
                logger.info(f"LLM ok | Ollama | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return r.json().get("response", "")
            except Exception as e:
                attempt += 1
                logger.warning(f"LLM error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    time.sleep(self.retry_delay)
        return ""

    def _generate_anthropic(self, prompt: str) -> str:
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                r = requests.post(
                    ANTHROPIC_URL,
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": ANTHROPIC_MODEL,
                        "max_tokens": 8192,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["content"][0]["text"]
                logger.info(f"LLM ok | Anthropic | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Anthropic error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                        delay = max(delay, 5)
                    time.sleep(delay)
        return ""

    def _generate_gemini(self, prompt: str) -> str:
        attempt = 0
        max_attempts = 5  # increased to handle rate limits
        while attempt <= max_attempts:
            try:
                start = time.time()
                r = requests.post(
                    GEMINI_URL,
                    headers={
                        "Authorization": f"Bearer {GEMINI_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       GEMINI_MODEL,
                        "messages":    [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM ok | Gemini | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Gemini error attempt {attempt}: {e}")
                if attempt <= max_attempts:
                    if "429" in str(e):
                        logger.warning("Gemini Rate Limit (429) hit. Waiting 30 seconds...")
                        time.sleep(30)
                    else:
                        time.sleep(15)
        return ""

    def _generate_sync(self, prompt: str) -> str:
        # Try Anthropic (Claude) first for best quality
        if self.use_anthropic:
            result = self._generate_anthropic(prompt)
            if result:
                return result
            logger.warning("Anthropic failed — falling back to Groq")
        if self.use_gemini:
            result = self._generate_gemini(prompt)
            if result:
                return result
        if self.use_groq:
            return self._generate_groq(prompt)
        return self._generate_ollama(prompt)

    def generate(self, prompt: str) -> str:
        return self._generate_sync(prompt)

    async def agenerate(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt)

    def _chat_groq(self, messages: list) -> str:
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                current_key = next(key_iterator)
                r = requests.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {current_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       GROQ_MODEL,
                        "messages":    messages,
                        "max_tokens":  GROQ_MAX_TOK,
                        "temperature": GROQ_TEMP,
                    },
                    timeout=60,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM ok | Groq Chat | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Groq Chat error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                        delay = max(delay, 5) # Minimum 5s backoff for 429
                    time.sleep(delay)
        return ""

    def _chat_ollama(self, messages: list) -> str:
        chat_url = self.url.replace("/api/generate", "/api/chat")
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                r = requests.post(
                    chat_url,
                    json={"model": self.model, "messages": messages, "stream": False},
                    timeout=self.timeout,
                )
                r.raise_for_status()
                logger.info(f"LLM ok | Ollama Chat | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return r.json().get("message", {}).get("content", "")
            except Exception as e:
                attempt += 1
                logger.warning(f"Ollama Chat error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    time.sleep(self.retry_delay)
        return ""

    def _chat_anthropic(self, messages: list) -> str:
        # Anthropic doesn't support 'system' messages in the messages array the same way,
        # it requires a separate 'system' parameter. We must extract it.
        system_text = ""
        anthropic_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
            else:
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})
                
        attempt = 0
        while attempt <= self.max_retries:
            try:
                start = time.time()
                payload = {
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 8192,
                    "messages": anthropic_msgs,
                }
                if system_text:
                    payload["system"] = system_text.strip()
                    
                r = requests.post(
                    ANTHROPIC_URL,
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=payload,
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["content"][0]["text"]
                logger.info(f"LLM ok | Anthropic Chat | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Anthropic Chat error attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                        delay = max(delay, 5)
                    time.sleep(delay)
        return ""

    def _chat_gemini(self, messages: list) -> str:
        attempt = 0
        max_attempts = 5
        while attempt <= max_attempts:
            try:
                start = time.time()
                r = requests.post(
                    GEMINI_URL,
                    headers={
                        "Authorization": f"Bearer {GEMINI_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       GEMINI_MODEL,
                        "messages":    messages,
                    },
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM chat ok | Gemini | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Gemini chat error attempt {attempt}: {e}")
                if attempt <= max_attempts:
                    if "429" in str(e):
                        logger.warning("Gemini Rate Limit (429) hit. Waiting 30 seconds...")
                        time.sleep(30)
                    else:
                        time.sleep(15)
        return ""

    def _chat_sync(self, messages: list) -> str:
        # Try Anthropic (Claude) first for best quality
        if self.use_anthropic:
            result = self._chat_anthropic(messages)
            if result:
                return result
            logger.warning("Anthropic chat failed — falling back to Groq")
        if self.use_gemini:
            result = self._chat_gemini(messages)
            if result:
                return result
        if self.use_groq:
            return self._chat_groq(messages)
        return self._chat_ollama(messages)

    async def achat(self, messages: list) -> str:
        return await asyncio.to_thread(self._chat_sync, messages)


# ─────────────────────────────────────────────────────────────────────────────
# Dedicated Gemini provider — ALWAYS uses Gemini regardless of env flags.
# Used by frontend_agent.py only (for quality React/UI code generation).
# All other agents use the main `llm` instance (Groq — fast, 30 RPM free tier).
# ─────────────────────────────────────────────────────────────────────────────
class GeminiLLMProvider:
    """Always uses Gemini API. Used exclusively by the frontend agent."""

    def _generate(self, prompt: str) -> str:
        attempt = 0
        max_attempts = 5
        while attempt <= max_attempts:
            try:
                start = time.time()
                r = requests.post(
                    GEMINI_URL,
                    headers={
                        "Authorization": f"Bearer {GEMINI_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":    GEMINI_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM ok | Gemini-Frontend | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Gemini-Frontend error attempt {attempt}: {e}")
                if attempt <= max_attempts:
                    if "429" in str(e):
                        logger.warning("Gemini rate limit hit — waiting 30s before retry...")
                        time.sleep(30)
                    else:
                        time.sleep(10)
        return ""

    def _chat(self, messages: list) -> str:
        attempt = 0
        max_attempts = 5
        while attempt <= max_attempts:
            try:
                start = time.time()
                r = requests.post(
                    GEMINI_URL,
                    headers={
                        "Authorization": f"Bearer {GEMINI_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":    GEMINI_MODEL,
                        "messages": messages,
                    },
                    timeout=120,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"LLM chat ok | Gemini-Frontend | attempt={attempt+1} | {round(time.time()-start,2)}s")
                return content
            except Exception as e:
                attempt += 1
                logger.warning(f"Gemini-Frontend chat error attempt {attempt}: {e}")
                if attempt <= max_attempts:
                    if "429" in str(e):
                        logger.warning("Gemini rate limit hit — waiting 30s before retry...")
                        time.sleep(30)
                    else:
                        time.sleep(10)
        return ""

    def generate(self, prompt: str) -> str:
        return self._generate(prompt)

    async def agenerate(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate, prompt)

    async def achat(self, messages: list) -> str:
        return await asyncio.to_thread(self._chat, messages)


# ─── Singletons ───────────────────────────────────────────────────────────────
# llm        → used by all agents (Gemini — high limits)
# llm_gemini → used by frontend agent only (Gemini — quality UI)
# ──────────────────────────────────────────────────────────────────────────────

llm        = LLMProvider()
llm_gemini = GeminiLLMProvider() if (USE_GEMINI and GEMINI_API_KEY) else llm