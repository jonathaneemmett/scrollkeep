from mcp.server.fastmcp import FastMCP

from mcp_server.llm import get_provider

mcp = FastMCP("mcp-server")
llm = get_provider()

def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()
