import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any, List, Optional
from groq import AsyncGroq

from core.circuit_breaker import get_breaker
from core.logger import setup_logger

logger = setup_logger("LLM_FALLBACK")

AVAILABLE_MODELS = {
    "llama-3.3-70b-versatile": {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B",
        "icon": "🚀",
        "description": "Best overall intelligence & versatility",
        "tier": "pro",
        "max_tokens": 4096,
    },
    "deepseek-r1-distill-llama-70b": {
        "id": "deepseek-r1-distill-llama-70b",
        "name": "DeepSeek R1 70B",
        "icon": "🧠",
        "description": "Deep reasoning & complex technical analysis",
        "tier": "pro",
        "max_tokens": 4096,
    },
    "mixtral-8x7b-32768": {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B",
        "icon": "⚡",
        "description": "High speed & large context handling",
        "tier": "pro",
        "max_tokens": 4096,
    },
    "llama-3.1-8b-instant": {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B",
        "icon": "⚡",
        "description": "Ultra-fast instant responses",
        "tier": "free",
        "max_tokens": 2048,
    },
    "gemma2-9b-it": {
        "id": "gemma2-9b-it",
        "name": "Gemma 2 9B",
        "icon": "💎",
        "description": "Efficient & concise replies",
        "tier": "free",
        "max_tokens": 2048,
    },
}

FALLBACK_HIERARCHY = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


@dataclass
class AIResponse:
    content: str
    model_used: str
    was_fallback: bool
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @property
    def error_type(self) -> Optional[str]:
        # Normalizes error strings so callers checking "rate_limit", "auth_error", etc. match cleanly
        if not self.error:
            return None
        if self.error == "rate_limited":
            return "rate_limit"
        if self.error == "invalid_key":
            return "auth_error"
        return self.error

    @property
    def error_message(self) -> str:
        return self.content if self.error else ""

    def get_formatted_content(self) -> str:
        if not self.content:
            return ""
        if self.was_fallback and self.model_used in AVAILABLE_MODELS:
            m_info = AVAILABLE_MODELS[self.model_used]
            return f"{self.content}\n\n<i>⚡ [Served via auto-fallback: {m_info['name']} due to primary model congestion]</i>"
        return self.content


class AIExecutionEngine:
    @classmethod
    def get_fallback_chain(cls, preferred_model: str = "llama-3.3-70b-versatile") -> List[str]:
        if preferred_model not in AVAILABLE_MODELS:
            preferred_model = "llama-3.3-70b-versatile"
        chain = [preferred_model]
        for model_id in FALLBACK_HIERARCHY:
            if model_id != preferred_model:
                chain.append(model_id)
        return chain

    @classmethod
    async def execute(
        cls,
        messages: List[dict],
        api_key: str,
        preferred_model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 2048,
        timeout: float = 30.0,
    ) -> AIResponse:
        if not api_key:
            return AIResponse(
                content="Your Groq API key is not set. Use /setkey to connect your free key.",
                model_used="none",
                was_fallback=False,
                error="invalid_key",
            )

        breaker = get_breaker("groq")
        if not breaker.can_execute():
            return AIResponse(
                content="⚠️ AI engine is currently resting due to momentary congestion. Please try again in 30 seconds.",
                model_used="none",
                was_fallback=False,
                error="circuit_open",
            )

        client = AsyncGroq(api_key=api_key, max_retries=1, timeout=timeout)
        chain = cls.get_fallback_chain(preferred_model)
        last_error = "unknown_error"

        for idx, model_id in enumerate(chain):
            try:
                # Adjust max_tokens if model has lower limit
                m_info = AVAILABLE_MODELS.get(model_id, {})
                adjusted_max_tokens = min(max_tokens, m_info.get("max_tokens", 4096))

                response = await client.chat.completions.create(
                    messages=messages,
                    model=model_id,
                    temperature=temperature,
                    max_tokens=adjusted_max_tokens,
                )
                raw_content = response.choices[0].message.content or ""
                breaker.record_success()

                was_fb = idx > 0
                if was_fb:
                    logger.info(f"Fallback triggered: {preferred_model} -> {model_id} succeeded.")

                return AIResponse(
                    content=raw_content,
                    model_used=model_id,
                    was_fallback=was_fb,
                    error=None,
                )

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate_limit" in error_str or "rate limit" in error_str:
                    logger.warning(f"Groq rate limit on {model_id}: {e}")
                    last_error = "rate_limited"
                elif "unauthorized" in error_str or "invalid" in error_str or "auth" in error_str or "401" in error_str:
                    logger.error(f"Groq API key invalid: {e}")
                    breaker.record_failure()
                    return AIResponse(
                        content="❌ That API key appears invalid or unauthorized. Please re-check at console.groq.com and run /setkey.",
                        model_used=model_id,
                        was_fallback=False,
                        error="invalid_key",
                    )
                elif "timeout" in error_str:
                    logger.warning(f"Groq timeout on {model_id}: {e}")
                    last_error = "timeout"
                else:
                    logger.warning(f"Groq error on {model_id}: {e}")
                    last_error = "server_error"

                breaker.record_failure()
                # Brief backoff before attempting next fallback
                if idx < len(chain) - 1:
                    await asyncio.sleep(0.4)

        # If all fallbacks failed
        if last_error == "rate_limited":
            err_content = "⏳ All AI models are temporarily at peak volume. Please try again in 1-2 minutes."
        elif last_error == "timeout":
            err_content = "⏱️ AI generation took too long across all fallback models. Please try a more concise query."
        else:
            err_content = "❌ AI engine encountered an unexpected issue across all available models. Please retry shortly."

        return AIResponse(
            content=err_content,
            model_used="none",
            was_fallback=False,
            error=last_error,
        )
