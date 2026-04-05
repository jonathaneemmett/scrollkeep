from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: SecretStr
    openai_api_key: SecretStr | None = None
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    workspace_dir: str = "~/.scrollkeep"
    telegram_bot_token: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
