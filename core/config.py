from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ChatApp DevSecOps API"
    app_version: str = "1.1.0"
    database_url: str = "sqlite:///./chat.db"
    cors_origins: str = "*"
    enable_unsafe_routes: bool = False
    moderation_keywords: str = Field(
        "password,secret,token,apikey,access key,private key",
        description="Comma separated keywords used by the moderation summary.",
    )

    model_config = {
        "case_sensitive": False,
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["*"]

    @property
    def moderation_keyword_list(self) -> list[str]:
        return [
            item.strip().lower()
            for item in self.moderation_keywords.split(",")
            if item.strip()
        ]


settings = Settings()
