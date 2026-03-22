# Scrollkeep Roadmap

## Completed

- ReAct agent loop with tool calling (Anthropic + OpenAI)
- Built-in tools: shell, file read/write/edit, structured memory, web search/fetch, delegate
- CLI REPL with streaming, rich markdown output, session management
- Tool confirmation with auto-approve for safe commands
- MCP client integration (connect to external MCP servers)
- Skills/plugin system (auto-load from ~/.scrollkeep/skills/)
- Multi-agent delegation
- Context window management (auto-trim old messages)
- Error handling with exponential backoff retry
- Input history with readline (arrow keys, persistent across sessions)
- CLI flags (--model, --provider, --new)
- `scrollkeep update` command
- Git tools (git_status, git_diff, git_log, git_commit) via `asyncio.create_subprocess_exec`
- Image/vision support (read_image tool, base64 encoding, Anthropic + OpenAI image content blocks)
- Conversation branching (`/undo` command, removes last user turn + all following messages)
- Prompt templates (`/template <name> [k=v ...]`, `/templates`, stored in `~/.scrollkeep/templates/`)
- Export sessions (`/export [path]`, formats conversation as readable markdown)
- Progress spinners (`rich.status.Status` — "Thinking…" / "tool running…")
- Configurable max tokens (`--max-tokens` flag, config setting)
- Token/cost tracking (usage display with estimated cost per turn)
- `--version` / `-V` flag
- Tab completion for `/` commands

---

## OpenClaw Feature Parity

These are the major features that OpenClaw has that Scrollkeep doesn't yet. These would bring Scrollkeep to full parity as a self-hosted personal AI assistant.

### 16. Gmail/Email Integration
Connect to Gmail via OAuth. Summarize unread emails, search threads, draft replies, auto-categorize, process attachments.

**Approach:** Build as a skill/plugin or dedicated tool module. Use Google's `google-api-python-client` and `google-auth-oauthlib` for OAuth2 + Gmail API. Store OAuth tokens locally in `~/.scrollkeep/credentials/`.

**Files to create/modify:**
- `src/mcp_server/tools/gmail.py` (NEW) — tools: `gmail_unread`, `gmail_summarize`, `gmail_search`, `gmail_draft_reply`, `gmail_send`
- `src/mcp_server/tools/__init__.py` (MODIFY) — import gmail module
- `src/mcp_server/agent/workspace.py` (MODIFY) — add credentials dir, update SOUL.md default
- `src/mcp_server/cli.py` (MODIFY) — add `scrollkeep gmail-auth` subcommand to run OAuth flow
- `pyproject.toml` (MODIFY) — add `google-api-python-client`, `google-auth-oauthlib` as optional deps
- `tests/test_gmail.py` (NEW)

### 17. Messaging Channel Integrations
Let users interact with Scrollkeep through WhatsApp, Telegram, Slack, Discord, and other messaging platforms instead of just the CLI.

**Approach:** Each channel is a separate async frontend that feeds messages into the same `agent_loop_streaming`. Start with Telegram (simplest API, no approval process). Use long-polling or webhooks.

**Files to create:**
- `src/mcp_server/channels/__init__.py` (NEW)
- `src/mcp_server/channels/telegram.py` (NEW) — Telegram Bot API via `aiohttp` (or `python-telegram-bot`)
- `src/mcp_server/channels/slack.py` (NEW) — Slack Bot via Socket Mode
- `src/mcp_server/channels/discord.py` (NEW) — Discord bot via `discord.py`
- `src/mcp_server/channels/whatsapp.py` (NEW) — WhatsApp Business API or Twilio
- `src/mcp_server/cli.py` (MODIFY) — add `scrollkeep serve --channel telegram` subcommand
- `src/mcp_server/config.py` (MODIFY) — add channel-specific config (bot tokens, etc.)
- `pyproject.toml` (MODIFY) — add channel deps as optional extras: `pip install scrollkeep[telegram]`

### 18. Browser Automation
Give the agent the ability to browse the web interactively — click, fill forms, take screenshots, extract content from JS-rendered pages.

**Approach:** Use Playwright (async API). Expose as tools: `browser_open`, `browser_click`, `browser_type`, `browser_screenshot`, `browser_extract`.

**Files to create/modify:**
- `src/mcp_server/tools/browser.py` (NEW) — Playwright-based tools, manage a shared browser instance
- `src/mcp_server/tools/__init__.py` (MODIFY) — conditional import (only if playwright installed)
- `src/mcp_server/agent/workspace.py` (MODIFY) — update SOUL.md default
- `pyproject.toml` (MODIFY) — add `playwright` as optional dep: `pip install scrollkeep[browser]`
- `tests/test_browser.py` (NEW)

### 19. Calendar Integration
Read and create calendar events. Google Calendar and/or Apple Calendar.

**Approach:** Google Calendar API (same OAuth flow as Gmail) or CalDAV for Apple Calendar.

**Files to create/modify:**
- `src/mcp_server/tools/calendar.py` (NEW) — tools: `calendar_today`, `calendar_upcoming`, `calendar_create`, `calendar_search`
- `src/mcp_server/tools/__init__.py` (MODIFY) — import calendar module
- `pyproject.toml` (MODIFY) — add calendar deps as optional
- `tests/test_calendar.py` (NEW)

### 20. Notes & Task Manager Integration
Connect to Apple Notes, Apple Reminders, Notion, Obsidian, Things 3, Trello.

**Approach:** Start with Obsidian (just read/write markdown files in a vault directory — no API needed). Notion via official API. Apple Notes/Reminders via AppleScript on macOS.

**Files to create/modify:**
- `src/mcp_server/tools/obsidian.py` (NEW) — tools that read/write/search markdown files in a configured vault path
- `src/mcp_server/tools/notion.py` (NEW) — Notion API integration
- `src/mcp_server/tools/apple.py` (NEW) — AppleScript bridge for Notes and Reminders (macOS only)
- `src/mcp_server/config.py` (MODIFY) — add vault paths, Notion API key, etc.
- `tests/test_obsidian.py` (NEW)

### 21. Voice Interface
Wake word detection and speech-to-text/text-to-speech for hands-free interaction.

**Approach:** Use `whisper` (or OpenAI Whisper API) for STT, system TTS for speech output. Wake word via `pvporcupine` or similar.

**Files to create/modify:**
- `src/mcp_server/channels/voice.py` (NEW) — microphone capture, STT, TTS, wake word loop
- `src/mcp_server/cli.py` (MODIFY) — add `scrollkeep voice` subcommand
- `pyproject.toml` (MODIFY) — add `openai-whisper`, `pyaudio` as optional deps

### 22. Proactive/Autonomous Tasks
Let the agent reach out to you proactively — scheduled briefings, reminders, monitoring alerts.

**Approach:** A background scheduler (using `asyncio` tasks or `APScheduler`) that runs agent loops on a schedule and delivers results via a configured channel (Telegram, Slack, etc.).

**Files to create/modify:**
- `src/mcp_server/scheduler.py` (NEW) — cron-like scheduler, stores tasks in `~/.scrollkeep/schedules.json`
- `src/mcp_server/cli.py` (MODIFY) — add `/schedule` command and `scrollkeep daemon` subcommand
- `tests/test_scheduler.py` (NEW)

### 23. Companion Apps
Native macOS menu bar app, iOS app, Android app for quick access.

**Approach:** This is a significant effort beyond the Python codebase. Options:
- macOS: `rumps` for a menu bar app that connects to a local Scrollkeep server via WebSocket
- Mobile: React Native or Flutter app that connects to Scrollkeep running on a home server
- All platforms: expose a local HTTP/WebSocket API first (`scrollkeep serve --api`), then build clients against it

**Files to create:**
- `src/mcp_server/api.py` (NEW) — FastAPI or aiohttp server exposing the agent loop as HTTP/WebSocket endpoints
- `apps/macos/` (NEW) — menu bar app
- `apps/mobile/` (NEW) — React Native or Flutter project
