from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str
    admin_telegram_ids: str
    webhook_secret: str
    webapp_url: str = ""
    azure_client_id: str = ""
    azure_storage_account_url: str
    azure_storage_container: str = "dream-media"
    cosmos_endpoint: str
    cosmos_database_name: str = "dream-palace"
    cosmos_users_container: str = "users"
    cosmos_dreams_container: str = "dreams"
    foundry_project_endpoint: str
    foundry_agent_name: str = "dream-analyst"

    @property
    def admins(self) -> frozenset[int]:
        return frozenset(int(value.strip()) for value in self.admin_telegram_ids.split(","))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
