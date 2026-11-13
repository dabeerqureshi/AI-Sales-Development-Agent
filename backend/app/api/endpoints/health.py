import time
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.health import (
    HealthResponse,
    DatabaseHealthResponse,
    OllamaHealthResponse,
)
from app.services.ollama_service import ollama_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Overall application health check."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version="0.1.0"
    )


@router.get("/health/database", response_model=DatabaseHealthResponse)
def get_database_health(
    response: Response,
    db: Session = Depends(get_db)
) -> DatabaseHealthResponse:
    """Verify SQLite database connectivity and query latency."""
    start_time = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return DatabaseHealthResponse(
            status="ok",
            connected=True,
            database_type="sqlite",
            latency_ms=latency_ms
        )
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(
            status="error",
            connected=False,
            database_type="sqlite",
            error=str(e)
        )


@router.get("/health/ollama", response_model=OllamaHealthResponse)
async def get_ollama_health(response: Response) -> OllamaHealthResponse:
    """Check Ollama service reachability and model availability."""
    is_reachable, model_found, models, error_msg = await ollama_service.check_health()
    
    if not is_reachable:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        status_text = "unreachable"
    elif not model_found:
        # Service is up, but model needs to be pulled
        status_text = "model_missing"
    else:
        status_text = "ok"

    return OllamaHealthResponse(
        status=status_text,
        ollama_reachable=is_reachable,
        configured_model=settings.OLLAMA_MODEL,
        model_available=model_found,
        available_models=models,
        error=error_msg or None
    )
