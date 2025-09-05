from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # Core
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key")
    openai_model: str = Field(default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), description="Model name")
    service_host: str = Field(default=os.getenv("SERVICE_HOST", "0.0.0.0"))
    service_port: int = Field(default=int(os.getenv("SERVICE_PORT", "8084")))
    request_timeout_seconds: int = Field(default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "8")))
    allow_origins: str = Field(default=os.getenv("ALLOW_ORIGINS", "*"), description="CORS origins (comma-separated)")

    # Security
    ira_shared_secret: str = Field(default=os.getenv("IRA_SHARED_SECRET", ""), description="Shared token required in X-IRA-Token header")
    ira_token_header: str = Field(default=os.getenv("IRA_TOKEN_HEADER", "X-IRA-Token"), description="Header name for shared token")

    # Cost/metrics (per 1K tokens)
    cost_input_per_1k: float = Field(default=float(os.getenv("COST_INPUT_PER_1K", "0") or 0.0))
    cost_output_per_1k: float = Field(default=float(os.getenv("COST_OUTPUT_PER_1K", "0") or 0.0))
    metrics_log_path: str = Field(default=os.getenv("METRICS_LOG_PATH", "services/llm/logs/llm_usage.jsonl"))
    metrics_file_log: bool = Field(default=os.getenv("METRICS_FILE_LOG", "1").lower() in ("1","true","yes"))

settings = Settings()

# If costs not provided, fall back to model defaults from models.py (per 1K)
try:
    if settings.cost_input_per_1k == 0 and settings.cost_output_per_1k == 0:
        from .models import default_prices_for
        _ci, _co = default_prices_for(settings.openai_model)
        if _ci is not None and _co is not None:
            settings.cost_input_per_1k = float(_ci)
            settings.cost_output_per_1k = float(_co)
except Exception:
    pass
