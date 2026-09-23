import logging

import httpx

from config import Config

logger = logging.getLogger(__name__)


class AIClient:
    """Provider-agnostic async chat client.

    Talks to any OpenAI-compatible ``/chat/completions`` endpoint over plain
    HTTP (via httpx). This removes the hard dependency on the OpenAI SDK, so
    the bot can point at OpenAI, a local model server (Ollama, LM Studio,
    vLLM, llama.cpp, ...), or any compatible gateway just by changing
    ``AI_API_BASE`` in the environment.
    """

    def __init__(self) -> None:
        # Normalize base URL (strip trailing slash) and build the endpoint.
        base = Config.AI_API_BASE.rstrip("/")
        self._url = f"{base}/chat/completions"
        self._headers = {"Content-Type": "application/json"}
        if Config.AI_API_KEY:
            self._headers["Authorization"] = f"Bearer {Config.AI_API_KEY}"

    async def chat(self, messages: list[dict]) -> tuple[str, int]:
        """
        Send messages to the AI model and return the assistant's reply.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            A tuple of (response_text, total_tokens_used).
        """
        payload = {
            "model": Config.AI_MODEL,
            "messages": messages,
            "max_tokens": Config.MAX_TOKENS,
            "temperature": Config.TEMPERATURE,
        }
        try:
            async with httpx.AsyncClient(timeout=Config.AI_TIMEOUT) as client:
                resp = await client.post(
                    self._url, headers=self._headers, json=payload
                )
                resp.raise_for_status()
                data = resp.json()

            choices = data.get("choices") or []
            text = ""
            if choices:
                text = (choices[0].get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            tokens = usage.get("total_tokens", 0) or 0
            return text, tokens
        except Exception as e:
            # Hide detailed error messages from users — log internally instead.
            logger.error(f"AI API error: {e}")
            return "⚠️ Sorry, I couldn't generate a response. Please try again later.", 0
