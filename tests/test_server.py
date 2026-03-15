from mcp_server.server import mcp


def test_server_exists() -> None:
    assert mcp is not None


def test_server_name() -> None:
    assert mcp.name == "mcp-server"