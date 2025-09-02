from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

# Always point to the service's own .env (../.env relative to this file)
ENV_PATH = (Path(__file__).resolve().parent.parent / ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8")
    openai_api_key: str = Field("", description="OpenAI API key")
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model")
    service_host: str = Field("0.0.0.0", description="Bind host")
    service_port: int = Field(8084, description="Bind port")
    request_timeout_seconds: int = Field(8, description="LLM request timeout (s)")
    allow_origins: str = Field("*", description="CORS origins (comma separated)")

settings = Settings()
