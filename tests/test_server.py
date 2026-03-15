from mcp_server.server import mcp


def test_server_exists():
    assert mcp is not None


def test_server_name():
    assert mcp.name == "mcp-server"