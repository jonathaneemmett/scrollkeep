import pytest

from mcp_server.server import mcp


@pytest.fixture
def server() -> object:
    return mcp