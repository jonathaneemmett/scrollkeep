from mcp.server.fastmcp import FastMCP

from mcp_server.llm import LLMProvider, get_provider

mcp = FastMCP("mcp-server", streamable_http_path="/")


def get_llm() -> LLMProvider:
    return get_provider()


def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()
