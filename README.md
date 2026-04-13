# Scrollkeep

A self-hosted personal AI assistant. Scrollkeep runs a ReAct-loop agent that can execute shell commands, read/write files, search the web, remember things across sessions, connect to MCP servers, and delegate subtasks to sub-agents. Connects to messaging channels (Telegram) and also functions as a Model Context Protocol (MCP) server.

## Quick Start

### Prerequisites

- **Docker** — [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **An Anthropic API key** — from [console.anthropic.com](https://console.anthropic.com)

### Install

```bash
# 1. Clone the repo
git clone https://github.com/jonathaneemmett/scrollkeep.git
cd scrollkeep

# 2. Configure
cp .env.example .env
```

Edit `.env` and set your API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Build

```bash
docker build -t scrollkeep .
```

### Run

Start the Telegram channel listener (default):

```bash
docker run -d \
  --restart unless-stopped \
  --env-file .env \
  -v ~/.scrollkeep:/home/appuser/.scrollkeep \
  --name scrollkeep \
  scrollkeep
```

Start an interactive CLI chat session:

```bash
docker run -it \
  --env-file .env \
  -v ~/.scrollkeep:/home/appuser/.scrollkeep \
  scrollkeep scrollkeep
```

The first run creates `~/.scrollkeep/` automatically with all workspace directories.

### Updating

Rebuild the container after pulling changes:

```bash
git pull
docker stop scrollkeep && docker rm scrollkeep
docker build -t scrollkeep .
docker run -d \
  --restart unless-stopped \
  --env-file .env \
  -v ~/.scrollkeep:/home/appuser/.scrollkeep \
  --name scrollkeep \
  scrollkeep
```

Or set up automatic deploys — see [Auto-Deploy with GitHub Actions](#auto-deploy-with-github-actions).

### Container Management

```bash
docker ps                  # check status
docker logs scrollkeep     # view logs
docker logs -f scrollkeep  # follow logs
docker restart scrollkeep  # restart
docker stop scrollkeep     # stop
```

## Auto-Deploy with GitHub Actions

Automatically rebuild and restart the container on every push to `main` using a self-hosted GitHub Actions runner.

### 1. Install the Runner

On the machine running Docker:

1. Go to your repo on GitHub: **Settings > Actions > Runners > New self-hosted runner**
2. Select your OS and architecture (e.g., **macOS**, **ARM64**)
3. Follow the provided commands to download and configure the runner

Install it as a service so it survives reboots:

```bash
cd actions-runner
./svc.sh install
./svc.sh start
```

### 2. Add the Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      - name: Rebuild and restart container
        run: |
          docker stop scrollkeep || true
          docker rm scrollkeep || true
          docker build -t scrollkeep .
          docker run -d \
            --restart unless-stopped \
            --env-file .env \
            -v ~/.scrollkeep:/home/appuser/.scrollkeep \
            --name scrollkeep \
            scrollkeep
```

Now every push to `main` will automatically rebuild and redeploy the container.

## Configuration

| Variable             | Required | Default                      | Description                          |
|----------------------|----------|------------------------------|--------------------------------------|
| `ANTHROPIC_API_KEY`  | Yes      | —                            | Anthropic API key                    |
| `OPENAI_API_KEY`     | No       | —                            | OpenAI API key (needed if using OpenAI) |
| `DEFAULT_PROVIDER`   | No       | `anthropic`                  | Which LLM provider to use by default |
| `DEFAULT_MODEL`      | No       | `claude-sonnet-4-20250514` | Which model to use                   |
| `WORKSPACE_DIR`      | No       | `~/.scrollkeep`              | Where sessions and memory are stored |
| `TELEGRAM_BOT_TOKEN` | No       | —                            | Telegram bot token for channel mode  |

Set these in the `.env` file at the project root, or export them as environment variables.

## Chat (CLI Agent)

```bash
docker run -it --env-file .env -v ~/.scrollkeep:/home/appuser/.scrollkeep scrollkeep scrollkeep
docker run -it --env-file .env -v ~/.scrollkeep:/home/appuser/.scrollkeep scrollkeep scrollkeep --new     # fresh session
docker run -it --env-file .env -v ~/.scrollkeep:/home/appuser/.scrollkeep scrollkeep scrollkeep -m gpt-4o -p openai  # use OpenAI
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
- **Telegram integration** — receive and respond to messages via Telegram bot

### Workspace

Scrollkeep stores its data in `~/.scrollkeep/` (mounted as a Docker volume):

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

## Development

For working on the code itself:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Test

```bash
pytest
```

### Lint & Type Check

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
├── channels/
│   ├── __init__.py
│   └── telegram.py        # Telegram bot channel
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
