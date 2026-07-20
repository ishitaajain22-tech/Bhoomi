"""
FastAPI app entrypoint. Wires up CORS (so the Vite frontend on
localhost:5173 can call this API), registers the three route
groups (crop, moisture, advisory), and exposes a /health check.
Run with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logger import configure_logging, get_logger
from app.api import routes_crop, routes_moisture, routes_advisory, routes_validation, routes_phenology, routes_methodology

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_crop.router, prefix=settings.api_v1_prefix)
app.include_router(routes_moisture.router, prefix=settings.api_v1_prefix)
app.include_router(routes_advisory.router, prefix=settings.api_v1_prefix)
app.include_router(routes_validation.router, prefix=settings.api_v1_prefix)
app.include_router(routes_phenology.router, prefix=settings.api_v1_prefix)
app.include_router(routes_methodology.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def on_startup():
    logger.info("%s starting up in '%s' mode", settings.app_name, settings.environment)
    _warm_caches()


def _warm_caches():
    """
    Every per-field lookup (rainfall/ETo/NDVI/SAR/model checkpoints)
    is cached lazily on first use — cheap after that, but it means
    whoever sends the very first request pays for loading every CSV
    and .pkl file at once. Priming with one real field here moves
    that cost to server startup instead of a judge's first click.
    """
    from datetime import date
    from app.models.advisory_engine import generate_advisory, _FIELD_COORDS

    if not _FIELD_COORDS:
        return
    first_field = next(iter(_FIELD_COORDS))
    try:
        generate_advisory(first_field, reference_date=date(2025, 3, 20))
        logger.info("Warmed data caches using field %s", first_field)
    except Exception:
        logger.exception("Cache warm-up failed — first real request will pay the cold-start cost instead")
