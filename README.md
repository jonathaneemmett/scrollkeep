# Scrollkeep

A Model Context Protocol (MCP) server with built-in LLM provider integration. MCP tools can delegate work to Anthropic (Claude) or OpenAI models through a common async interface.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copy the example env file and add your API keys:

```bash
cp .env.example .env
```

| Variable             | Required | Default      | Description                          |
|----------------------|----------|--------------|--------------------------------------|
| `ANTHROPIC_API_KEY`  | Yes      | —            | Anthropic API key                    |
| `OPENAI_API_KEY`     | No       | —            | OpenAI API key (needed if using OpenAI) |
| `DEFAULT_PROVIDER`   | No       | `anthropic`  | Which LLM provider to use by default |
| `LOG_LEVEL`          | No       | `INFO`       | Logging verbosity                    |

## Run

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
├── tools/             # Tool modules go here
│   └── __init__.py
└── llm/               # LLM provider abstraction
    ├── __init__.py
    ├── base.py        # LLMProvider protocol
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

# Call the LLM
result = await llm.complete(
    messages=[{"role": "user", "content": "Summarize this text..."}],
    model="claude-sonnet-4-20250514",
)
```
