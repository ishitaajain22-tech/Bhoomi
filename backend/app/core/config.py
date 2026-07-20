"""
Central app configuration, loaded from environment variables.
Keeps API keys, data paths, and model paths in one typed place
instead of scattered os.environ calls across the codebase.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Bhoomi Backend"
    api_v1_prefix: str = "/api"
    environment: str = "development"

    # CORS — Vite picks the next free port (5174, 5175...) if 5173 is
    # already busy, so a couple of neighbouring ports + the 127.0.0.1
    # form are allowed too rather than requiring an exact match.
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]

    # Satellite data access (Copernicus / Sentinel Hub)
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""

    # Local data paths
    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"
    model_checkpoint_dir: str = "ml/checkpoints"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
