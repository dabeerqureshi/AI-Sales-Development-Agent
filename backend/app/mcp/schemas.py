from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BusinessDiscoveryResult(BaseModel):
    business_name: str = Field(..., description="Official or trading name of the business")
    industry: str = Field(..., description="Business category or amenity")
    website: Optional[str] = Field(None, description="Official website URL")
    phone: Optional[str] = Field(None, description="Public phone number")
    address: Optional[str] = Field(None, description="Formatted physical address")
    latitude: Optional[float] = Field(None, description="Geographic latitude")
    longitude: Optional[float] = Field(None, description="Geographic longitude")
    external_id: str = Field(..., description="Unique OpenStreetMap element ID (e.g. node/123)")
    source_url: str = Field(..., description="Verifiable OpenStreetMap source link")
    source_name: str = Field(default="OpenStreetMap/Overpass", description="Data provider name")
    raw_tags: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw tag key-values")


class MCPToolInfo(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


class MCPServerInfo(BaseModel):
    name: str
    transport: str = "stdio"
    status: str = "active"
    available_tools: List[MCPToolInfo] = []


class MCPToolExecutionLog(BaseModel):
    server_name: str
    tool_name: str
    input_summary: str
    execution_status: str
    execution_time_ms: float
    error_message: Optional[str] = None
