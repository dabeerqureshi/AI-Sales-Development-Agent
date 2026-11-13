import pytest
from fastapi.testclient import TestClient
from app.mcp.manager import mcp_manager


def test_mcp_servers_endpoint(client: TestClient):
    response = client.get("/api/mcp/servers")
    assert response.status_code == 200
    servers = response.json()
    assert len(servers) >= 1
    assert servers[0]["name"] == "openstreetmap"
    assert servers[0]["transport"] == "stdio"
    assert servers[0]["status"] == "active"


def test_mcp_tools_endpoint(client: TestClient):
    response = client.get("/api/mcp/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 1
    tool_names = [t["name"] for t in tools]
    assert "search_businesses" in tool_names


def test_mcp_status_endpoint(client: TestClient):
    response = client.get("/api/mcp/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["status"] == "healthy"
    assert status_data["registered_servers"] >= 1
    assert status_data["available_tools"] >= 1


@pytest.mark.asyncio
async def test_mcp_manager_unapproved_tool():
    with pytest.raises(ValueError, match="not in the approved MCP registry"):
        await mcp_manager.execute_tool(
            tool_name="unapproved_system_exec",
            arguments={"cmd": "ls"},
        )


@pytest.mark.asyncio
async def test_mcp_manager_missing_arguments():
    with pytest.raises(ValueError, match="Missing required arguments"):
        await mcp_manager.execute_tool(
            tool_name="search_businesses",
            arguments={"city": "Austin"},  # missing industry and country
        )
