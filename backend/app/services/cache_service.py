import hashlib
import json
from dataclasses import dataclass


class CachedResult:
    def __init__(self, reply: str, input_tokens: int, output_tokens: int) -> None:
        self.reply, self.input_tokens, self.output_tokens = reply, input_tokens, output_tokens


class CacheService:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._entries: dict[str, CachedResult] = {}

    @staticmethod
    def key(model: str, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"model": model, "messages": messages}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, model: str, messages: list[dict[str, str]]) -> CachedResult | None:
        return self._entries.get(self.key(model, messages)) if self.enabled else None

    def put(self, model: str, messages: list[dict[str, str]], result: CachedResult) -> None:
        if self.enabled:
            self._entries[self.key(model, messages)] = result

