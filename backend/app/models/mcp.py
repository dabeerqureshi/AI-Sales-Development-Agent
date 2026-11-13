from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from app.models.base import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    transport = Column(String(50), default="stdio")
    status = Column(String(50), default="active")  # active, offline, error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class MCPToolExecution(Base):
    __tablename__ = "mcp_tool_executions"

    id = Column(Integer, primary_key=True, index=True)
    server_name = Column(String(100), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    input_summary = Column(Text, nullable=False)
    execution_status = Column(String(50), nullable=False)  # success, error, timeout
    execution_time_ms = Column(Float, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
