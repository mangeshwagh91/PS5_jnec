from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Integrated Multi-Threat Surveillance API"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"

    detection_confidence_threshold: float = 0.55
    dedup_window_seconds: int = 120
    simulation_enabled: bool = True
    simulation_interval_seconds: int = 6
    stats_cache_ttl_seconds: int = 5
    ingestion_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
