import os
import logging
import asyncio
from groq import Groq

logger = logging.getLogger("AI-Digital-Company")

class GroqProvider:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.client  = Groq(api_key=self.api_key)
        logger.info(f"GroqProvider ready | model={self.model}")

    async def generate(self, prompt: str, timeout: int = 120) -> str:
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=4096,
                        temperature=0.7,
                    )
                )
                result = response.choices[0].message.content
                logger.info(f"Groq ok | attempt={attempt}")
                return result
            except Exception as e:
                logger.warning(f"Groq error attempt {attempt}: {e}")
                if attempt == max_attempts:
                    logger.warning("Groq failed all attempts -- using fallback")
                    return ""
                await asyncio.sleep(2 ** attempt)
        return ""