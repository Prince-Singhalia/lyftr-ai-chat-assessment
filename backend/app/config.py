from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_api_keys: str = ""
    llm_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    fallback_llm_enabled: bool = False
    fallback_llm_model: str = "groq/openai/gpt-oss-20b"
    llm_api_base: str | None = None
    database_url: str = "sqlite:///./data/app.db"
    allowed_origins: str = "http://localhost:3000"
    enable_failure_simulation: bool = False
    litellm_cache: bool = True
    cache_dir: str = "/data/cache"
    environment: str = "development"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def api_keys(self) -> list[str]:
        return [key.strip() for key in self.llm_api_keys.split(",") if key.strip()]

    @property
    def groq_key(self) -> str | None:
        return self.groq_api_key.strip() or None

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

