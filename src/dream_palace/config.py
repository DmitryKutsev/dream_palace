from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    clerk_bot_token: str
    dreamer_bot_token: str
    admin_telegram_ids: str
    google_cloud_project: str
    firebase_storage_bucket: str
    adk_model: str = "gemini-2.0-flash"
    webhook_secret: str = ""

    @property
    def admins(self) -> frozenset[int]:
        return frozenset(int(value.strip()) for value in self.admin_telegram_ids.split(","))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
