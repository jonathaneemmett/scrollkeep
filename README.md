# Scrollkeep

A self-hosted personal AI assistant with a CLI chat interface. Scrollkeep runs a ReAct-loop agent that can execute shell commands, read/write files, search the web, remember things across sessions, connect to MCP servers, and delegate subtasks to sub-agents. Also functions as a Model Context Protocol (MCP) server.

## Quick Start

### Prerequisites

- **Python 3.11+** — check with `python3 --version`
- **pipx** — for isolated global installs
- **An Anthropic API key** — from [console.anthropic.com](https://console.anthropic.com)

Install prerequisites on macOS:

```bash
brew install python@3.11 pipx
pipx ensurepath   # add pipx bin dir to your PATH (restart your shell after)
```

### Install

```bash
# 1. Clone the repo
git clone https://github.com/your-org/scrollkeep.git
cd scrollkeep

# 2. Install globally (makes `scrollkeep` available anywhere)
pipx install -e .

# 3. Configure
cp .env.example .env
```

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Run

```bash
scrollkeep          # start (resumes latest session)
```

The first run creates `~/.scrollkeep/` automatically with all workspace directories.

### Updating

Since this is an editable install, code changes are picked up immediately — just `git pull`. If dependencies change:

```bash
scrollkeep update
```

### Development Install

For working on the code itself (includes test/lint tooling):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

With the dev install, run via `.venv/bin/scrollkeep` or activate the venv first.

## Configuration

| Variable             | Required | Default                      | Description                          |
|----------------------|----------|------------------------------|--------------------------------------|
| `ANTHROPIC_API_KEY`  | Yes      | —                            | Anthropic API key                    |
| `OPENAI_API_KEY`     | No       | —                            | OpenAI API key (needed if using OpenAI) |
| `DEFAULT_PROVIDER`   | No       | `anthropic`                  | Which LLM provider to use by default |
| `DEFAULT_MODEL`      | No       | `claude-sonnet-4-20250514` | Which model to use                   |
| `WORKSPACE_DIR`      | No       | `~/.scrollkeep`              | Where sessions and memory are stored |

Set these in the `.env` file at the project root, or export them as environment variables.

## Chat (CLI Agent)

```bash
scrollkeep                          # resume latest session
scrollkeep --new                    # start fresh session
scrollkeep --model gpt-4o --provider openai  # use OpenAI
scrollkeep -m claude-sonnet-4-20250514 -n    # short flags
```

### REPL Commands

| Command      | Description          |
|--------------|----------------------|
| `/new`       | Start a new session  |
| `/sessions`  | List all sessions    |
| `/help`      | Show help            |
| `exit`/`quit`| Quit                 |

### Built-in Tools

| Tool | Description |
|------|-------------|
| `shell_exec` | Run shell commands |
| `read_file` | Read file contents |
| `write_file` | Write content to a file |
| `edit_file` | Replace text in a file |
| `save_memory` | Save a memory with title, content, and tags |
| `search_memory` | Search memories by keyword |
| `list_memories` | List all saved memories |
| `delete_memory` | Delete a memory by name |
| `web_search` | Search the web via DuckDuckGo |
| `web_fetch` | Fetch and read a URL |
| `delegate` | Delegate a subtask to a sub-agent |

### Features

- **Streaming responses** — tokens print as they arrive
- **Tool confirmation** — prompts before executing tools, with auto-approve for safe commands (ls, cat, read_file, etc.)
- **Rich output** — markdown rendering with syntax highlighting
- **Structured memory** — tagged memories with search
- **Session persistence** — quit and restart, history is restored
- **Context management** — automatically trims old messages to stay within token limits
- **Error handling** — exponential backoff retry on rate limits and transient API errors
- **Input history** — arrow keys, line editing, and persistent command history across sessions
- **MCP client** — connect to external MCP servers for more tools
- **Skills/plugins** — drop Python files in `~/.scrollkeep/skills/`
- **Multi-agent** — delegate subtasks to independent sub-agents

### Workspace

Scrollkeep stores its data in `~/.scrollkeep/`:

```
~/.scrollkeep/
├── SOUL.md            # System prompt (customize personality)
├── mcp_servers.json   # External MCP server definitions
├── input_history      # Persistent command history
├── memory/            # Structured memory files
├── sessions/          # JSONL session logs
└── skills/            # Custom tool plugins (.py files)
```

### MCP Server Integration

Create `~/.scrollkeep/mcp_servers.json` to connect external MCP servers:

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  }
}
```

Tools from connected servers are namespaced (e.g., `filesystem__read_file`).

### Custom Skills

Drop a `.py` file in `~/.scrollkeep/skills/`:

```python
from mcp_server.tools.registry import registry

@registry.tool("weather", "Get the current weather for a city")
async def weather(city: str) -> str:
    # your implementation here
    return f"Weather for {city}: sunny, 72°F"
```

Skills are loaded automatically at startup.

## MCP Server Mode

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

## Project Structure

```
src/mcp_server/
├── __init__.py
├── server.py              # MCP server entrypoint
├── config.py              # Settings via pydantic-settings
├── logging.py             # Structured logging setup
├── cli.py                 # CLI chat REPL
├── tools/
│   ├── __init__.py
│   ├── registry.py        # Tool registry with auto-schema generation
│   ├── builtins.py        # File and shell tools
│   ├── memory.py          # Structured memory tools
│   ├── web.py             # Web search and fetch tools
│   ├── delegate.py        # Sub-agent delegation tool
│   ├── skills.py          # Plugin loader
│   └── mcp_client.py      # External MCP server client
├── agent/
│   ├── __init__.py
│   ├── loop.py            # ReAct agent loop (standard + streaming)
│   ├── workspace.py       # Workspace & system prompt management
│   └── session.py         # JSONL session persistence
└── llm/
    ├── __init__.py
    ├── base.py            # LLMProvider protocol
    ├── types.py           # Shared types (ToolSchema, ToolCall, LLMResponse)
    ├── anthropic.py       # Anthropic provider (with streaming)
    ├── openai.py          # OpenAI provider (with streaming)
    └── factory.py         # get_provider() factory
```
