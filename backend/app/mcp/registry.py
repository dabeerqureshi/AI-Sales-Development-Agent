from typing import Any, Callable, Dict, List, Optional
from app.mcp.schemas import MCPToolInfo, MCPServerInfo

APPROVED_TOOLS: Dict[str, Dict[str, Any]] = {
    "search_businesses": {
        "server": "openstreetmap",
        "description": "Discover businesses from OpenStreetMap/Overpass API by industry, city, and country.",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "Business industry/category"},
                "city": {"type": "string", "description": "City name"},
                "country": {"type": "string", "description": "Country name"},
                "state_or_region": {"type": "string", "description": "Optional state or region"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 50},
            },
            "required": ["industry", "city", "country"],
        },
    }
}


def get_registered_servers() -> List[MCPServerInfo]:
    return [
        MCPServerInfo(
            name="openstreetmap",
            transport="stdio",
            status="active",
            available_tools=[
                MCPToolInfo(
                    name=tool_name,
                    description=meta["description"],
                    input_schema=meta["parameters"],
                )
                for tool_name, meta in APPROVED_TOOLS.items()
                if meta["server"] == "openstreetmap"
            ],
        )
    ]


def get_registered_tools() -> List[MCPToolInfo]:
    return [
        MCPToolInfo(
            name=tool_name,
            description=meta["description"],
            input_schema=meta["parameters"],
        )
        for tool_name, meta in APPROVED_TOOLS.items()
    ]
