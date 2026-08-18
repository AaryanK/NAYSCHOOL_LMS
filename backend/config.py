import json
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "NaySchool 3.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./nayschool.db"
    SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    DEFAULT_AI_PROVIDER: str = "auto"
    ALLOW_CLOUD_AI: bool = True

    OLLAMA_BASE_URL: str = "https://ollama.com/api"
    OLLAMA_DEFAULT_MODEL: str = "qwen3-coder:480b"
    OLLAMA_API_KEY: str | None = None

    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "deepseek/deepseek-chat"

    DEEPSEEK_API_KEY: str | None = None
    DEEP_SEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_DEFAULT_MODEL: str = "deepseek-chat"

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    ENABLE_SEMANTIC_SEARCH: bool = True
    SEMANTIC_TOP_K: int = 5
    KEYWORD_TOP_K: int = 5
    HYBRID_SEARCH_TOP_K: int = 5
    AUTO_EMBED_ON_UPLOAD: bool = True

    CORS_ORIGINS: Union[str, List[str]] = '["http://127.0.0.1:8000", "http://localhost:8000"]'

    # LMS integration configurations
    LMS_INTEGRATIONS_ENABLED: bool = True
    TOKEN_ENCRYPTION_KEY: str | None = None

    # Blackboard Settings
    BLACKBOARD_ENABLED: bool = False
    BLACKBOARD_BASE_URL: str | None = None
    BLACKBOARD_CLIENT_ID: str | None = None
    BLACKBOARD_CLIENT_SECRET: str | None = None
    BLACKBOARD_APP_ID: str | None = None
    BLACKBOARD_REDIRECT_URI: str = "http://127.0.0.1:8000/api/lms/blackboard/oauth/callback"
    BLACKBOARD_SCOPES: str = "read"

    # Canvas Settings
    CANVAS_ENABLED: bool = False
    CANVAS_BASE_URL: str | None = None
    CANVAS_CLIENT_ID: str | None = None
    CANVAS_CLIENT_SECRET: str | None = None
    CANVAS_REDIRECT_URI: str = "http://127.0.0.1:8000/api/lms/canvas/oauth/callback"


    @property
    def get_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        try:
            return json.loads(self.CORS_ORIGINS)
        except Exception:
            return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]

    @property
    def get_deepseek_key(self) -> Union[str, None]:
        return self.DEEPSEEK_API_KEY or self.DEEP_SEEK_API_KEY

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
