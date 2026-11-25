import logging
import re
from dataclasses import dataclass
from typing import Any

from ..config import Settings
from .cache_service import CacheService, CachedResult
from .token_service import estimate_tokens, usage_value

logger = logging.getLogger(__name__)

class ProvidersUnavailable(Exception):
    pass


class SimulatedProviderError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("simulated provider failure")
        self.status_code = status_code


@dataclass
class GatewayResult:
    reply: str
    source: str
    model: str
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class LLMGateway:
    def __init__(self, settings: Settings, cache: CacheService | None = None) -> None:
        self.settings = settings
        self.keys = settings.api_keys
        self.cache = cache or CacheService(settings.litellm_cache)
        # LiteLLM is imported lazily so health checks and deterministic tests do not
        # pay the provider SDK import cost. The pinned dependency is installed in
        # the runtime image and is loaded immediately before a real call.
        self.cache_initialized = bool(settings.litellm_cache)

    @staticmethod
    def _simulation(header: str | None) -> dict[str, int]:
        values: dict[str, int] = {}
        if not header:
            return values
        for item in header.split(","):
            key, _, status = item.strip().partition("=")
            if key and status in {"429", "500", "502", "503"}:
                values[key] = int(status)
        return values

    def complete(self, messages: list[dict[str, str]], failure_header: str | None = None) -> GatewayResult:
        model = self.settings.llm_model
        simulated = self._simulation(failure_header) if self.settings.enable_failure_simulation else {}
        if not simulated:
            cached = self.cache.get(model, messages)
            if cached:
                return GatewayResult(cached.reply, "LLM_CACHE", cached.model or model, cached.input_tokens, cached.output_tokens, None, 0)
        if not self.keys:
            raise ProvidersUnavailable()
        failures = 0
        retryable_failures = True
        for index, api_key in enumerate(self.keys, start=1):
            key_id = f"key_{index}"
            try:
                if "*" in simulated or key_id in simulated:
                    raise SimulatedProviderError(simulated.get(key_id, simulated.get("*", 503)))
                result = self._complete_for_provider(messages, api_key, model, key_id, failures)
                self.cache.put(model, messages, CachedResult(result.reply, result.input_tokens, result.output_tokens, result.model))
                return result
            except Exception as error:
                logger.warning("LLM provider attempt failed key_id=%s exception=%s status=%s category=%s error=%s",
                    key_id, type(error).__name__, _http_status(error), _error_category(error),
                    _safe_error_message(error, self.keys))
                failures += 1
                retryable_failures = retryable_failures and _is_retryable(error)
        if not retryable_failures:
            raise ProvidersUnavailable()
        if len(self.keys) < 2 or not self.settings.fallback_llm_enabled or not self.settings.groq_key:
            raise ProvidersUnavailable()
        try:
            if "*" in simulated or "groq" in simulated or "fallback" in simulated:
                status = simulated.get("groq", simulated.get("fallback", simulated.get("*", 503)))
                raise SimulatedProviderError(status)
            groq_result = self._complete_for_provider(messages, self.settings.groq_key, self.settings.fallback_llm_model, "groq", failures)
            self.cache.put(model, messages, CachedResult(groq_result.reply, groq_result.input_tokens, groq_result.output_tokens, groq_result.model))
            return groq_result
        except Exception as error:
            logger.warning("LLM provider attempt failed key_id=groq exception=%s status=%s category=%s error=%s",
                type(error).__name__, _http_status(error), _error_category(error),
                _safe_error_message(error, self.keys + ([self.settings.groq_key] if self.settings.groq_key else [])))
        raise ProvidersUnavailable()

    def _complete_for_provider(self, messages: list[dict[str, str]], api_key: str, model: str, key_id: str, failures: int) -> GatewayResult:
        response = self._call_litellm(messages, api_key) if model == self.settings.llm_model else self._call_litellm(messages, api_key, model)
        reply = self._content(response)
        usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        input_tokens = usage_value(usage, "prompt_tokens", "input_tokens") or estimate_tokens(" ".join(m["content"] for m in messages))
        output_tokens = usage_value(usage, "completion_tokens", "output_tokens") or estimate_tokens(reply)
        return GatewayResult(reply, "LIVE_INFERENCE", model, input_tokens, output_tokens, key_id, failures)

    def _call_litellm(self, messages: list[dict[str, str]], api_key: str, model: str | None = None) -> Any:
        import litellm
        from litellm import Cache
        _quiet_provider_transport_logs()
        if self.settings.litellm_cache and getattr(litellm, "cache", None) is None:
            litellm.cache = Cache()
        kwargs: dict[str, Any] = {"model": model or self.settings.llm_model, "messages": messages, "api_key": api_key, "timeout": 30}
        if self.settings.llm_api_base:
            kwargs["api_base"] = self.settings.llm_api_base
        return litellm.completion(**kwargs)

    def diagnose_keys(self, model: str = "gemini/gemini-3.8-flash") -> list[dict[str, Any]]:
        """Run an uncached, independent live Gemini probe for each configured key."""
        prompt = "Reply with exactly: Gemini connection successful."
        results = []
        for index, api_key in enumerate(self.keys, start=1):
            key_id = f"key_{index}"
            try:
                response = self._diagnostic_completion(model, api_key, prompt)
                self._content(response)
                results.append({"key_id": key_id, "success": True, "model": model, "error_category": None, "http_status": None})
            except Exception as error:
                logger.warning("Gemini diagnostic failed key_id=%s exception=%s status=%s category=%s error=%s",
                    key_id, type(error).__name__, _http_status(error), _error_category(error),
                    _safe_error_message(error, self.keys))
                results.append({"key_id": key_id, "success": False, "model": model,
                    "error_category": _error_category(error), "http_status": _http_status(error)})
        return results

    def _diagnostic_completion(self, model: str, api_key: str, prompt: str) -> Any:
        import litellm
        _quiet_provider_transport_logs()
        kwargs: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": prompt}], "api_key": api_key, "timeout": 20}
        if self.settings.llm_api_base:
            kwargs["api_base"] = self.settings.llm_api_base
        # Diagnostic requests must reach the provider even if ordinary LiteLLM
        # caching is enabled. Temporarily suspend the global cache and restore it.
        original_cache = getattr(litellm, "cache", None)
        litellm.cache = None
        try:
            return litellm.completion(**kwargs)
        finally:
            litellm.cache = original_cache

    @staticmethod
    def _content(response: Any) -> str:
        if isinstance(response, dict):
            return response["choices"][0]["message"]["content"]
        return response.choices[0].message.content


def _http_status(error: Exception) -> int | None:
    status = getattr(error, "status_code", None) or getattr(error, "http_status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _error_category(error: Exception) -> str:
    status = _http_status(error)
    name = type(error).__name__.lower()
    message = str(error).lower()
    if status == 429 or "ratelimit" in name or "rate limit" in message or "quota" in message:
        return "rate_limit"
    if status == 401 or status == 403 or "auth" in name or "invalid api key" in message:
        return "authentication"
    if status == 404 or "notfound" in name or "model not found" in message:
        return "model_not_found"
    if "timeout" in name or "timed out" in message:
        return "timeout"
    if status is not None and status >= 500:
        return "provider_server_error"
    if "connection" in name or "network" in message or "connecterror" in name:
        return "network"
    return "provider_error"


def _is_retryable(error: Exception) -> bool:
    status = _http_status(error)
    if status in {408, 429, 500, 502, 503, 504}:
        return True
    if status is not None:
        return False
    category = _error_category(error)
    return category in {"timeout", "network"}


def _safe_error_message(error: Exception, secrets: list[str]) -> str:
    message = str(error)
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    message = re.sub(r"(?i)(AIza[0-9A-Za-z_-]{20,})", "[REDACTED]", message)
    message = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+", r"\1[REDACTED]", message)
    message = re.sub(r"(?i)(api[_ -]?key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", message)
    message = re.sub(r"https?://\S+", "[URL]", message)
    return message[:500]


def _quiet_provider_transport_logs() -> None:
    # httpx logs Gemini's API key in the URL query string at INFO level.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    try:
        import litellm
        litellm.set_verbose = False
    except ImportError:
        pass

