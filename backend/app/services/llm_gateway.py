from dataclasses import dataclass
from typing import Any

from ..config import Settings
from .cache_service import CacheService, CachedResult
from .token_service import estimate_tokens, usage_value

class ProvidersUnavailable(Exception):
    pass


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
                return GatewayResult(cached.reply, "LLM_CACHE", model, cached.input_tokens, cached.output_tokens, None, 0)
        if not self.keys:
            raise ProvidersUnavailable()
        failures = 0
        for index, api_key in enumerate(self.keys, start=1):
            key_id = f"key_{index}"
            try:
                if "*" in simulated or key_id in simulated:
                    raise RuntimeError("simulated provider failure")
                response = self._call_litellm(messages, api_key)
                reply = self._content(response)
                usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
                input_tokens = usage_value(usage, "prompt_tokens", "input_tokens") or estimate_tokens(" ".join(m["content"] for m in messages))
                output_tokens = usage_value(usage, "completion_tokens", "output_tokens") or estimate_tokens(reply)
                result = GatewayResult(reply, "LIVE_INFERENCE", model, input_tokens, output_tokens, key_id, failures)
                self.cache.put(model, messages, CachedResult(reply, input_tokens, output_tokens))
                return result
            except Exception:
                failures += 1
        raise ProvidersUnavailable()

    def _call_litellm(self, messages: list[dict[str, str]], api_key: str) -> Any:
        import litellm
        from litellm import Cache
        if self.settings.litellm_cache and getattr(litellm, "cache", None) is None:
            litellm.cache = Cache()
        kwargs: dict[str, Any] = {"model": self.settings.llm_model, "messages": messages, "api_key": api_key, "cache": self.settings.litellm_cache}
        if self.settings.llm_api_base:
            kwargs["api_base"] = self.settings.llm_api_base
        return litellm.completion(**kwargs)

    @staticmethod
    def _content(response: Any) -> str:
        if isinstance(response, dict):
            return response["choices"][0]["message"]["content"]
        return response.choices[0].message.content

