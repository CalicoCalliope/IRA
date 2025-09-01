from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model to use")
    service_host: str = Field("0.0.0.0", description="Host to bind FastAPI service")
    service_port: int = Field(8084, description="Port to bind FastAPI service")
    request_timeout_seconds: int = Field(8, description="Timeout in seconds for LLM requests")
    allow_origins: str = Field("*", description="Allowed CORS origins (comma separated)")

    class Config:
        env_file = ".env"  # only used locally

settings = Settings()