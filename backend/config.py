from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    default_provider: str = "groq"
    database_url: str = ""
    github_token: str = ""
    vercel_token: str = ""
    vercel_scope: str = ""  # Team slug for CLI, e.g. anshumans-projects-671c73a5
    cors_origins: str = (
        "http://localhost:3000,"
        "https://intelligent-harness-system-12345.vercel.app"
    )
    workspace_root: str = "../workspace"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def provider_keys(self) -> dict:
        return {
            "groq": self.groq_api_key,
            "gemini": self.gemini_api_key,
            "openrouter": self.openrouter_api_key,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
