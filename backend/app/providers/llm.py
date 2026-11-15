from __future__ import annotations
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

CANNED_REPORT_JSON = json.dumps({
    "executive_summary": "This is a mock research summary.",
    "key_findings": ["Finding 1", "Finding 2"],
    "observations": "Some observations.",
    "contradictions": None,
    "limitations": "Mock provider — no real analysis performed.",
    "sources_used": ["[SOURCE 1]", "[SOURCE 2]"],
})


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM and return the response text."""
        ...


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: int, base_url: str | None = None):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout, base_url=base_url)
        self._model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        metrics.increment("llm_calls_total", labels={"provider": "openai"})
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""


class MockLLMProvider(LLMProvider):
    """Deterministic mock for testing. Returns a canned JSON response."""

    def __init__(self, response: str | None = None, fail: bool = False, fail_times: int = 0):
        self._response = response or CANNED_REPORT_JSON
        self._fail = fail
        self._fail_times = fail_times
        self._call_count = 0

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        metrics.increment("llm_calls_total", labels={"provider": "mock"})
        self._call_count += 1
        if self._fail or (self._fail_times > 0 and self._call_count <= self._fail_times):
            raise RuntimeError("MockLLMProvider: simulated failure")
        return self._response


class WatsonxProvider(LLMProvider):
    """IBM watsonx.ai provider using ibm-watsonx-ai SDK."""

    def __init__(self, api_key: str, url: str, project_id: str, model_id: str, timeout: int):
        self._api_key = api_key
        self._url = url
        self._project_id = project_id
        self._model_id = model_id
        self._timeout = timeout
        self._model = None

    def _get_model(self):
        if self._model is None:
            from ibm_watsonx_ai import APIClient, Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference

            credentials = Credentials(url=self._url, api_key=self._api_key)
            client = APIClient(credentials)
            self._model = ModelInference(
                model_id=self._model_id,
                api_client=client,
                project_id=self._project_id,
                # max_new_tokens is for text-generation; chat API uses max_tokens
                params={"max_tokens": 4096},
            )
        return self._model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        metrics.increment("llm_calls_total", labels={"provider": "watsonx"})
        import asyncio

        model = self._get_model()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]
        # ibm-watsonx-ai chat() is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.chat(messages=messages),
        )
        # response is a dict: {"choices": [{"message": {"content": "..."}}]}
        choices = response.get("choices", [])
        if not choices:
            raise RuntimeError("watsonx.ai returned an empty response")
        return choices[0].get("message", {}).get("content", "")


class GeminiProvider(LLMProvider):
    """Google Gemini provider via google-genai SDK (new official SDK).

    Free tier: 1,500 requests/day, 1M token context window.
    API keys: https://aistudio.google.com/app/apikey
    Default model: gemini-2.5-flash
    """

    def __init__(self, api_key: str, model: str, timeout: int):
        from google import genai
        from google.genai import types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        self._model_name = model
        self._timeout = timeout

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        metrics.increment("llm_calls_total", labels={"provider": "gemini"})
        import asyncio
        from google.genai import types

        coro = self._client.aio.models.generate_content(
            model=self._model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )
        response = await asyncio.wait_for(coro, timeout=self._timeout)
        return response.text or ""


class GroqProvider(LLMProvider):
    """Groq Cloud provider — fast inference, generous free tier.

    Default model: qwen/qwen3.8-27b (or llama-3.3-70b-versatile).
    API keys: https://console.groq.com/keys
    """

    def __init__(self, api_key: str, model: str, timeout: int):
        from groq import AsyncGroq
        self._client = AsyncGroq(api_key=api_key, timeout=timeout, max_retries=0)
        self._model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        metrics.increment("llm_calls_total", labels={"provider": "groq"})
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""


class FallbackLLMProvider(LLMProvider):
    """Tries the primary provider first. On rate-limit (429), quota exhaustion,
    or token limit errors, automatically retries with each fallback provider in order.

    Fallback triggers on: HTTP 429/402/403/404, 'consumption_limit_reached',
    'rate_limit_exceeded', 'quota', 'token limit', 'resource has been exhausted',
    'failed to retrieve project', etc.

    Caches the active working fallback provider to avoid repeated failing calls
    against an exhausted primary provider.
    """

    _RATE_LIMIT_SIGNALS = (
        "429",
        "402",
        "403",
        "404",
        "consumption_limit_reached",
        "rate_limit_exceeded",
        "rate_limit",
        "ratelimit",
        "quota",
        "too many requests",
        "limit reached",
        "limit exceeded",
        "token limit",
        "tokens limit",
        "token quota",
        "plan limit",
        "plan_limit",
        "capacity exceeded",
        "resource has been exhausted",
        "exhausted",
        "billing",
        "credit",
        "insufficient_quota",
        "payment required",
        "cannotsetprojectorspace",
        "failed to retrieve project",
        "not_found: deleted",
        "project is deleted",
        "inactive or deleted",
        "overloaded",
        "service unavailable",
    )

    def __init__(self, primary: LLMProvider, fallbacks: list[LLMProvider]):
        self._primary = primary
        self._fallbacks = fallbacks
        self._active_provider: LLMProvider | None = None

    def _is_rate_limit(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(sig in msg for sig in self._RATE_LIMIT_SIGNALS)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        # If a fallback provider was previously latched as working, try it first
        if self._active_provider is not None:
            try:
                return await self._active_provider.complete(system_prompt, user_prompt)
            except Exception as active_exc:
                logger.warning(
                    "FallbackLLMProvider: active fallback %s failed (%s) — re-checking chain",
                    type(self._active_provider).__name__,
                    active_exc,
                )
                self._active_provider = None

        # Try primary
        try:
            result = await self._primary.complete(system_prompt, user_prompt)
            return result
        except Exception as primary_exc:
            if not self._is_rate_limit(primary_exc):
                raise  # non-rate-limit/non-quota errors propagate immediately

            logger.warning(
                "FallbackLLMProvider: primary %s failed with quota/token limit (%s) — trying fallbacks",
                type(self._primary).__name__,
                primary_exc,
            )

        # Try each fallback in order
        last_exc: Exception = RuntimeError("All LLM providers failed")
        for i, fallback in enumerate(self._fallbacks):
            try:
                logger.info(
                    "FallbackLLMProvider: attempting fallback %d (%s)",
                    i + 1,
                    type(fallback).__name__,
                )
                result = await fallback.complete(system_prompt, user_prompt)
                logger.info(
                    "FallbackLLMProvider: fallback %d (%s) succeeded — latching as active provider",
                    i + 1,
                    type(fallback).__name__,
                )
                self._active_provider = fallback
                return result
            except Exception as fb_exc:
                logger.warning(
                    "FallbackLLMProvider: fallback %d (%s) failed: %s",
                    i + 1,
                    type(fallback).__name__,
                    fb_exc,
                )
                last_exc = fb_exc

        raise last_exc


def _build_primary(settings) -> LLMProvider:
    """Build the primary LLM provider from settings."""
    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "watsonx":
        api_key = getattr(settings, "WATSONX_API_KEY", "") or settings.LLM_API_KEY
        model = getattr(settings, "WATSONX_MODEL", "meta-llama/llama-3-3-70b-instruct") if settings.LLM_MODEL.startswith("gemini") or settings.LLM_MODEL == "gpt-4o-mini" else settings.LLM_MODEL
        return WatsonxProvider(
            api_key=api_key,
            url=settings.WATSONX_URL,
            project_id=settings.WATSONX_PROJECT_ID,
            model_id=model,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "groq":
        api_key = settings.LLM_API_KEY or getattr(settings, "GROQ_API_KEY", "")
        model = settings.LLM_MODEL if settings.LLM_MODEL != "gpt-4o-mini" else getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b")
        return GroqProvider(
            api_key=api_key,
            model=model,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "gemini":
        api_key = settings.LLM_API_KEY or getattr(settings, "GEMINI_API_KEY", "")
        model = settings.LLM_MODEL if settings.LLM_MODEL != "gpt-4o-mini" else getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "openrouter":
        api_key = settings.LLM_API_KEY or getattr(settings, "OPENROUTER_API_KEY", "")
        model = settings.LLM_MODEL if settings.LLM_MODEL != "gpt-4o-mini" else getattr(settings, "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
        return OpenAIProvider(
            api_key=api_key,
            model=model,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            base_url="https://openrouter.ai/api/v1",
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")


def _build_fallbacks(settings) -> list[LLMProvider]:
    """Build ordered fallback providers from FALLBACK_LLM_PROVIDERS setting.

    FALLBACK_LLM_PROVIDERS is a comma-separated list: e.g. 'gemini,groq,openrouter'
    Each provider uses its own API key setting:
      gemini    → GEMINI_API_KEY     + GEMINI_MODEL
      groq      → GROQ_API_KEY       + GROQ_MODEL
      openrouter→ OPENROUTER_API_KEY + OPENROUTER_MODEL
      watsonx   → WATSONX_URL + WATSONX_PROJECT_ID + LLM_API_KEY
      openai    → OPENAI_API_KEY     + OPENAI_FALLBACK_MODEL
    """
    fallbacks: list[LLMProvider] = []
    raw = getattr(settings, "FALLBACK_LLM_PROVIDERS", "") or ""
    for name in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            if name == "gemini":
                key = getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
                model = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
                if key:
                    fallbacks.append(GeminiProvider(api_key=key, model=model, timeout=60))
                else:
                    logger.warning("FallbackLLM: gemini listed but GEMINI_API_KEY not set — skipping")
            elif name == "groq":
                key = getattr(settings, "GROQ_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
                model = getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b")
                if key:
                    fallbacks.append(GroqProvider(api_key=key, model=model, timeout=60))
                else:
                    logger.warning("FallbackLLM: groq listed but GROQ_API_KEY not set — skipping")
            elif name == "openrouter":
                key = getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
                model = getattr(settings, "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
                if key:
                    # OpenRouter is OpenAI-compatible — reuse OpenAIProvider with custom base_url
                    fallbacks.append(OpenAIProvider(
                        api_key=key,
                        model=model,
                        timeout=60,
                        base_url="https://openrouter.ai/api/v1",
                    ))
                else:
                    logger.warning("FallbackLLM: openrouter listed but OPENROUTER_API_KEY not set — skipping")
            elif name == "watsonx":
                key = getattr(settings, "WATSONX_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
                url = getattr(settings, "WATSONX_URL", "")
                project_id = getattr(settings, "WATSONX_PROJECT_ID", "")
                model = getattr(settings, "WATSONX_MODEL", "meta-llama/llama-3-3-70b-instruct")
                if key and url and project_id:
                    fallbacks.append(WatsonxProvider(
                        api_key=key,
                        url=url,
                        project_id=project_id,
                        model_id=model,
                        timeout=60,
                    ))
                else:
                    logger.warning("FallbackLLM: watsonx listed but credentials not set — skipping")
            elif name == "openai":
                key = getattr(settings, "OPENAI_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
                model = getattr(settings, "OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
                if key:
                    fallbacks.append(OpenAIProvider(api_key=key, model=model, timeout=60))
                else:
                    logger.warning("FallbackLLM: openai listed but OPENAI_API_KEY not set — skipping")
            else:
                logger.warning("FallbackLLM: unknown fallback provider %r — skipping", name)
        except Exception as exc:
            logger.warning("FallbackLLM: failed to build fallback %r: %s — skipping", name, exc)
    return fallbacks


_cached_llm_provider: LLMProvider | None = None


def get_llm_provider(reload: bool = False) -> LLMProvider:
    """Return the configured LLM provider, wrapped in FallbackLLMProvider
    if FALLBACK_LLM_PROVIDERS is set. Caches the provider instance to avoid
    re-instantiation latency on every node."""
    global _cached_llm_provider
    if _cached_llm_provider is not None and not reload:
        return _cached_llm_provider

    from app.core.config import settings

    primary = _build_primary(settings)
    fallbacks = _build_fallbacks(settings)

    if fallbacks:
        _cached_llm_provider = FallbackLLMProvider(primary=primary, fallbacks=fallbacks)
    else:
        _cached_llm_provider = primary
    return _cached_llm_provider
