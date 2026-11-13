from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.session import get_db
from app.models.mcp import MCPToolExecution
from app.mcp.manager import mcp_manager
from app.mcp.schemas import MCPServerInfo, MCPToolExecutionLog, MCPToolInfo

router = APIRouter()


@router.get("/mcp/servers", response_model=List[MCPServerInfo])
def get_mcp_servers() -> List[MCPServerInfo]:
    """List all registered MCP servers and connection status."""
    return mcp_manager.get_servers()


@router.get("/mcp/tools", response_model=List[MCPToolInfo])
def get_mcp_tools() -> List[MCPToolInfo]:
    """List all approved MCP tools and schemas."""
    return mcp_manager.get_tools()


@router.get("/mcp/status")
def get_mcp_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve runtime status of the MCP integration subsystem."""
    servers = mcp_manager.get_servers()
    tools = mcp_manager.get_tools()

    recent_exec_stmt = (
        select(MCPToolExecution)
        .order_by(MCPToolExecution.created_at.desc())
        .limit(1)
    )
    last_exec = db.scalar(recent_exec_stmt)

    return {
        "status": "healthy" if servers else "unconfigured",
        "registered_servers": len(servers),
        "available_tools": len(tools),
        "servers": [s.model_dump() for s in servers],
        "last_execution": (
            {
                "tool": last_exec.tool_name,
                "status": last_exec.execution_status,
                "duration_ms": last_exec.execution_time_ms,
                "timestamp": last_exec.created_at,
            }
            if last_exec
            else None
        ),
    }


@router.get("/mcp/executions", response_model=List[MCPToolExecutionLog])
def list_mcp_executions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[MCPToolExecutionLog]:
    """Retrieve recent MCP tool execution audit logs."""
    stmt = (
        select(MCPToolExecution)
        .order_by(MCPToolExecution.created_at.desc())
        .limit(limit)
    )
    executions = db.scalars(stmt).all()
    return [
        MCPToolExecutionLog(
            server_name=e.server_name,
            tool_name=e.tool_name,
            input_summary=e.input_summary,
            execution_status=e.execution_status,
            execution_time_ms=e.execution_time_ms,
            error_message=e.error_message,
        )
        for e in executions
    ]
