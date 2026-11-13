from typing import List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    version: str = "0.1.0"


class DatabaseHealthResponse(BaseModel):
    status: str
    connected: bool
    database_type: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class OllamaHealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    configured_model: str
    model_available: bool
    available_models: List[str] = []
    error: Optional[str] = None
