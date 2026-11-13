import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import init_db
from app.api.endpoints import health, campaigns, mcp, research, contacts, qualification, emails, crm, gmail, worker

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_sdr")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite database schema
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down AI Sales Development Agent backend.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Local-first AI Sales Development Agent API backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount health endpoints at root as required
app.include_router(health.router, tags=["Health"])

# Mount API v1 Routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health (v1)"])
app.include_router(campaigns.router, prefix="/api", tags=["Campaigns & Leads"])
app.include_router(campaigns.router, prefix=f"{settings.API_V1_STR}", tags=["Campaigns & Leads (v1)"])
app.include_router(mcp.router, prefix="/api", tags=["MCP Subsystem"])
app.include_router(mcp.router, prefix=f"{settings.API_V1_STR}", tags=["MCP Subsystem (v1)"])
app.include_router(research.router, prefix="/api", tags=["Website Research"])
app.include_router(research.router, prefix=f"{settings.API_V1_STR}", tags=["Website Research (v1)"])
app.include_router(contacts.router, prefix="/api", tags=["Public Contacts"])
app.include_router(contacts.router, prefix=f"{settings.API_V1_STR}", tags=["Public Contacts (v1)"])
app.include_router(qualification.router, prefix="/api", tags=["Lead Qualification & Scoring"])
app.include_router(qualification.router, prefix=f"{settings.API_V1_STR}", tags=["Lead Qualification & Scoring (v1)"])
app.include_router(emails.router, prefix="/api", tags=["AI Email Studio"])
app.include_router(emails.router, prefix=f"{settings.API_V1_STR}", tags=["AI Email Studio (v1)"])
app.include_router(crm.router, prefix="/api", tags=["CRM Pipeline & Suppression"])
app.include_router(crm.router, prefix=f"{settings.API_V1_STR}", tags=["CRM Pipeline & Suppression (v1)"])
app.include_router(gmail.router, prefix="/api", tags=["Gmail API & Dispatch"])
app.include_router(gmail.router, prefix=f"{settings.API_V1_STR}", tags=["Gmail API & Dispatch (v1)"])
app.include_router(worker.router, prefix="/api", tags=["Follow-up Engine & Worker"])
app.include_router(worker.router, prefix=f"{settings.API_V1_STR}", tags=["Follow-up Engine & Worker (v1)"])


@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs"
    }
