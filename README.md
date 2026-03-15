# Scrollkeep

A self-hosted personal AI assistant with a CLI chat interface. Scrollkeep runs a ReAct-loop agent that can execute shell commands, read/write files, and remember things across sessions. Also functions as a Model Context Protocol (MCP) server.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copy the example env file and add your API keys:

```bash
cp .env.example .env
```

| Variable             | Required | Default                      | Description                          |
|----------------------|----------|------------------------------|--------------------------------------|
| `ANTHROPIC_API_KEY`  | Yes      | —                            | Anthropic API key                    |
| `OPENAI_API_KEY`     | No       | —                            | OpenAI API key (needed if using OpenAI) |
| `DEFAULT_PROVIDER`   | No       | `anthropic`                  | Which LLM provider to use by default |
| `DEFAULT_MODEL`      | No       | `claude-sonnet-4-20250514` | Which model to use                   |
| `WORKSPACE_DIR`      | No       | `~/.scrollkeep`              | Where sessions and memory are stored |

## Chat (CLI Agent)

```bash
scrollkeep
```

This launches an interactive REPL. The agent can:

- **Run shell commands** — "list the files in this directory"
- **Read/write/edit files** — "create a file called notes.txt with today's date"
- **Remember things** — writes to `~/.scrollkeep/MEMORY.md`
- **Persist sessions** — quit and restart, conversation history is restored

### Workspace

Scrollkeep stores its data in `~/.scrollkeep/`:

```
~/.scrollkeep/
├── SOUL.md        # System prompt (customize the agent's personality)
├── MEMORY.md      # Persistent memory
└── sessions/      # JSONL session logs
```

## MCP Server

```bash
python -m mcp_server.server
```

## Test

```bash
pytest
```

## Lint & Type Check

```bash
ruff check .
mypy src/
```

## Docker

```bash
docker build -t scrollkeep .
docker run scrollkeep
```

## Project Structure

```
src/mcp_server/
├── __init__.py
├── server.py          # MCP server entrypoint
├── config.py          # Settings via pydantic-settings
├── logging.py         # Structured logging setup
├── cli.py             # CLI chat REPL
├── tools/
│   ├── __init__.py
│   ├── registry.py    # Tool registry with auto-schema generation
│   └── builtins.py    # Built-in tools (shell, read, write, edit)
├── agent/
│   ├── __init__.py
│   ├── loop.py        # ReAct agent loop
│   ├── workspace.py   # Workspace & system prompt management
│   └── session.py     # JSONL session persistence
└── llm/
    ├── __init__.py
    ├── base.py        # LLMProvider protocol
    ├── types.py       # Shared types (ToolSchema, ToolCall, LLMResponse)
    ├── anthropic.py   # Anthropic (Claude) provider
    ├── openai.py      # OpenAI provider
    └── factory.py     # get_provider() factory
```

## LLM Usage

```python
from mcp_server.llm import get_provider

# Uses default provider from settings
llm = get_provider()

# Or specify explicitly
llm = get_provider("openai")

# Simple completion
result = await llm.complete(
    messages=[{"role": "user", "content": "Summarize this text..."}],
    model="claude-sonnet-4-20250514",
)

# Completion with tool calling
from mcp_server.llm.types import LLMResponse
response: LLMResponse = await llm.complete_with_tools(
    messages=[{"role": "user", "content": "What files are here?"}],
    model="claude-sonnet-4-20250514",
    tools=registry.schemas(),
    system="You are a helpful assistant.",
)
```
