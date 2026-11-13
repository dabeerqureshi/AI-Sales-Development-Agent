import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and verify connectivity."""
    from app.models.base import Base
    import app.models.setting  # noqa: F401
    import app.models.campaign  # noqa: F401
    import app.models.lead  # noqa: F401
    import app.models.mcp  # noqa: F401
    import app.models.research  # noqa: F401
    import app.models.contact  # noqa: F401
    import app.models.score  # noqa: F401
    import app.models.email  # noqa: F401
    import app.models.crm  # noqa: F401
    import app.models.gmail  # noqa: F401
    import app.models.worker  # noqa: F401
    
    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            if settings.DATABASE_URL.startswith("sqlite"):
                conn.execute(text("PRAGMA journal_mode=WAL;"))
                conn.execute(text("PRAGMA busy_timeout=5000;"))
                conn.commit()
        logger.info("Database initialized with WAL mode and connectivity confirmed.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
