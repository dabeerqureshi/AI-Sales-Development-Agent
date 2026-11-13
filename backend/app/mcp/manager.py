import json
import logging
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.mcp import MCPToolExecution
from app.mcp.registry import APPROVED_TOOLS, get_registered_servers, get_registered_tools
from app.mcp.schemas import BusinessDiscoveryResult, MCPServerInfo, MCPToolInfo
from app.mcp.servers.openstreetmap import search_businesses

logger = logging.getLogger("mcp_manager")


class MCPManager:
    """Manages Model Context Protocol (MCP) tool registry, validation, execution and logging."""

    def __init__(self):
        self._servers = get_registered_servers()
        self._tools = get_registered_tools()

    def get_servers(self) -> List[MCPServerInfo]:
        """Return list of connected/registered MCP servers."""
        return self._servers

    def get_tools(self) -> List[MCPToolInfo]:
        """Return list of all approved MCP tools."""
        return self._tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> List[BusinessDiscoveryResult]:
        """
        Execute an approved MCP tool with argument validation, runtime timing,
        and audit persistence.
        """
        if tool_name not in APPROVED_TOOLS:
            raise ValueError(f"Tool '{tool_name}' is not in the approved MCP registry.")

        tool_meta = APPROVED_TOOLS[tool_name]
        server_name = tool_meta["server"]
        start_time = time.time()
        status = "success"
        error_msg = None
        results: List[BusinessDiscoveryResult] = []

        input_summary = json.dumps(
            {k: v for k, v in arguments.items() if k not in ["secret", "token"]},
            default=str,
        )

        try:
            if tool_name == "search_businesses":
                # Validate required args
                industry = arguments.get("industry")
                city = arguments.get("city")
                country = arguments.get("country")
                state_or_region = arguments.get("state_or_region")
                limit = int(arguments.get("limit", 50))

                if not (industry and city and country):
                    raise ValueError("Missing required arguments: 'industry', 'city', and 'country' are required.")

                raw_businesses = await search_businesses(
                    industry=industry,
                    city=city,
                    country=country,
                    state_or_region=state_or_region,
                    limit=limit,
                )

                # Validate and parse each returned business through Pydantic
                for b in raw_businesses:
                    try:
                        results.append(BusinessDiscoveryResult(**b))
                    except Exception as parse_err:
                        logger.warning(f"Skipping malformed discovery element: {parse_err}")

            else:
                raise NotImplementedError(f"Handler for tool '{tool_name}' is not implemented.")

        except Exception as e:
            status = "error"
            error_msg = str(e)
            logger.error(f"Error executing MCP tool '{tool_name}': {e}", exc_info=True)
            raise
        finally:
            execution_time_ms = round((time.time() - start_time) * 1000, 2)
            if db:
                try:
                    execution_log = MCPToolExecution(
                        server_name=server_name,
                        tool_name=tool_name,
                        input_summary=input_summary,
                        execution_status=status,
                        execution_time_ms=execution_time_ms,
                        error_message=error_msg,
                    )
                    db.add(execution_log)
                    db.commit()
                except Exception as log_err:
                    logger.warning(f"Failed to record MCP execution log: {log_err}")

        return results


mcp_manager = MCPManager()
