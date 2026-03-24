from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_service():
    """Create a mock Gmail API service."""
    svc = MagicMock()

    # Reset the cached service before and after each test
    import mcp_server.tools.gmail as gmail_mod
    gmail_mod._service = svc
    yield svc
    gmail_mod._service = None


def _make_message(
    msg_id: str = "abc123",
    thread_id: str = "thread1",
    subject: str = "Test Subject",
    sender: str = "alice@example.com",
    date: str = "Mon, 1 Jan 2026 10:00:00 +0000",
    body_text: str = "Hello world",
) -> dict:
    """Build a fake Gmail API message resource."""
    return {
        "id": msg_id,
        "threadId": thread_id,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": "me@example.com"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": date},
                {"name": "Message-ID", "value": f"<{msg_id}@mail.example.com>"},
            ],
            "body": {
                "data": base64.urlsafe_b64encode(body_text.encode()).decode(),
            },
        },
    }


@pytest.mark.asyncio
async def test_gmail_unread(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_unread

    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg1"}, {"id": "msg2"}],
    }
    mock_service.users().messages().get().execute.return_value = _make_message()

    result = await gmail_unread(max_results=5)
    assert "2 unread" in result
    assert "Test Subject" in result


@pytest.mark.asyncio
async def test_gmail_unread_empty(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_unread

    mock_service.users().messages().list().execute.return_value = {"messages": []}

    result = await gmail_unread()
    assert "No unread" in result


@pytest.mark.asyncio
async def test_gmail_search(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_search

    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg1"}],
    }
    mock_service.users().messages().get().execute.return_value = _make_message(
        subject="Invoice from Acme"
    )

    result = await gmail_search(query="invoice")
    assert "1 results" in result
    assert "Invoice from Acme" in result


@pytest.mark.asyncio
async def test_gmail_search_no_results(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_search

    mock_service.users().messages().list().execute.return_value = {"messages": []}

    result = await gmail_search(query="nonexistent")
    assert "No messages found" in result


@pytest.mark.asyncio
async def test_gmail_summarize(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_summarize

    mock_service.users().messages().get().execute.return_value = _make_message(
        body_text="Meeting at 3pm tomorrow."
    )

    result = await gmail_summarize(message_id="msg1")
    assert "Meeting at 3pm tomorrow." in result
    assert "Test Subject" in result


@pytest.mark.asyncio
async def test_gmail_draft_reply(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_draft_reply

    mock_service.users().messages().get().execute.return_value = _make_message()
    mock_service.users().drafts().create().execute.return_value = {"id": "draft1"}

    result = await gmail_draft_reply(message_id="msg1", body="Sounds good!")
    assert "Draft created" in result
    assert "draft1" in result


@pytest.mark.asyncio
async def test_gmail_send(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_send

    mock_service.users().messages().send().execute.return_value = {"id": "sent1"}

    result = await gmail_send(
        to="bob@example.com", subject="Hi Bob", body="Just checking in."
    )
    assert "Sent to bob@example.com" in result
    assert "Hi Bob" in result


@pytest.mark.asyncio
async def test_extract_body_multipart(mock_service: MagicMock) -> None:
    from mcp_server.tools.gmail import gmail_summarize

    multipart_msg = _make_message()
    multipart_msg["payload"] = {
        "mimeType": "multipart/alternative",
        "headers": multipart_msg["payload"]["headers"],
        "body": {},
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Plain text version").decode(),
                },
            },
            {
                "mimeType": "text/html",
                "body": {
                    "data": base64.urlsafe_b64encode(b"<p>HTML version</p>").decode(),
                },
            },
        ],
    }
    mock_service.users().messages().get().execute.return_value = multipart_msg

    result = await gmail_summarize(message_id="msg1")
    assert "Plain text version" in result
