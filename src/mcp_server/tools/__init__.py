import mcp_server.tools.builtins  # noqa: F401 — registers tools
import mcp_server.tools.delegate  # noqa: F401 — registers delegate tool
import mcp_server.tools.memory  # noqa: F401 — registers memory tools
import mcp_server.tools.web  # noqa: F401 — registers web tools
from mcp_server.tools.registry import registry

__all__ = ["registry"]