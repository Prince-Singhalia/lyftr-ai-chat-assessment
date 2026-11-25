"""Run a live per-key Gemini probe without reading or writing conversation data."""
import json
import logging

from .config import get_settings
from .services.llm_gateway import LLMGateway


def main() -> int:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    gateway = LLMGateway(settings)
    results = gateway.diagnose_keys(model=settings.llm_model)
    print(json.dumps(results, indent=2))
    return 0 if results and all(item["success"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
