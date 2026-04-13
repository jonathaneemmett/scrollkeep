from __future__ import annotations

import base64
import json
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from mcp_server.tools.registry import registry

# Lazy imports - only available if gmail extras installed
_service = None

def _get_credentials_path() -> Path:
    return Path("~/.scrollkeep/credentials").expanduser()

def _get_service():
    global _service
    if _service is not None:
        return _service

    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly", 
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",     
    ]

    creds_dir = _get_credentials_path()
    token_path = creds_dir / "gmail_token.json"
    client_secret_path = creds_dir / "gmail_client_secret.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(
                    f"Gmail token refresh failed: {e}. "
                    "Run `scrollkeep gmail-auth` to re-authenticate."
                ) from e
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"Place your Google OAuth client_secret.json at {client_secret_path}\n"               
                    "Get one from https://console.cloud.google.com/apis/credentials"                      
                ) 
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())

    _service = build('gmail', 'v1', credentials=creds)
    return _service

async def run_oauth_flow() -> None:
    """Called by `scrollkeep gmail-auth` to authenticate."""   
    try:
        svc = _get_service()
        profile = svc.users().getProfile(userId="me").execute()
        print(f"Authenticated as {profile['emailAddress']}")
    except FileNotFoundError as e:
        print(e)

def _parse_headers(headers: list[dict]) -> dict[str, str]:
    result = {}
    for h in headers:
        if h["name"] in ["From", "To", "Subject", "Date"]:
            result[h["name"]] = h["value"]
    return result

@registry.tool("gmail_unread", "List unread emails from Gmail inbox")
async def gmail_unread(max_results: int = 10) -> str:
    svc = _get_service()
    results = svc.users().messages().list(
        userId="me", 
        q="is:unread", 
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return "No unread messages found."
    
    lines = []
    for msg_ref in messages:
        msg = svc.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",                                             
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()                                                                                       
        headers = _parse_headers(msg["payload"]["headers"])
        lines.append(                                                                                     
            f"- **{headers.get('Subject', '(no subject)')}** "
            f"from {headers.get('From', 'unknown')} "                                                     
            f"({headers.get('Date', '')})"                                                                
        )                                                                                                 
                                                                                                        
    return f"{len(messages)} unread:\n" + "\n".join(lines) 

@registry.tool("gmail_search", "Search Gmail for messages matching a query")
async def gmail_search(query: str, max_results: int = 10) -> str:
    svc = _get_service()                                                                                  
    results = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results                                                      
    ).execute()                                           

    messages = results.get("messages", [])                                                                
    if not messages:
        return f"No messages found for: {query}"                                                          
                                                        
    lines = []
    for msg_ref in messages:
        msg = svc.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",                                             
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()                                                                                       
        headers = _parse_headers(msg["payload"]["headers"])
        lines.append(
            f"- [{msg_ref['id'][:8]}] **{headers.get('Subject', '(no subject)')}** "                      
            f"from {headers.get('From', 'unknown')} ({headers.get('Date', '')})"                          
        )                                                                                                 
                                                                                                        
    return f"{len(messages)} results:\n" + "\n".join(lines)

                                                                                                        
@registry.tool("gmail_summarize", "Read and return the full content of an email by message ID")
async def gmail_summarize(message_id: str) -> str:                                                        
    svc = _get_service()                                  
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()                                                                                           

    headers = _parse_headers(msg["payload"]["headers"])                                                   
    header_str = "\n".join(f"**{k}:** {v}" for k, v in headers.items())
                                                                                                        
    # Extract body
    body = _extract_body(msg["payload"])                                                                  
                                                                                                        
    return f"{header_str}\n\n{body}"
                                                                                                        
                                                        
def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):                   
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")        
                                                                                                        
    for part in payload.get("parts", []):                                                                 
        text = _extract_body(part)                                                                        
        if text:                                                                                          
            return text
                                                                                                        
    # Fallback: try HTML                                  
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")        

    return "(no readable body)"                                                                           
                                                        
                                                                                                        
@registry.tool("gmail_draft_reply", "Draft a reply to an email (does not send)")
async def gmail_draft_reply(message_id: str, body: str) -> str:                                           
    svc = _get_service()                                  
    original = svc.users().messages().get(
        userId="me", id=message_id, format="metadata",                                                    
        metadataHeaders=["From", "Subject", "Message-ID"]
    ).execute()                                                                                           
                                                        
    headers = _parse_headers(original["payload"]["headers"])
    msg_id_header = next(
        (h["value"] for h in original["payload"]["headers"] if h["name"] == "Message-ID"), None           
    )                                                                                                     
                                                                                                        
    subject = headers.get("Subject", "")                                                                  
    if not subject.lower().startswith("re:"):             
        subject = f"Re: {subject}"

    message = MIMEText(body)                                                                              
    message["to"] = headers.get("From", "")
    message["subject"] = subject                                                                          
    if msg_id_header:                                     
        message["In-Reply-To"] = msg_id_header
        message["References"] = msg_id_header                                                             

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()                                           
    draft = svc.users().drafts().create(                  
        userId="me",                                                                                      
        body={"message": {"raw": raw, "threadId": original.get("threadId")}}
    ).execute()                                                                                           

    return f"Draft created (id: {draft['id']}) — reply to {headers.get('From', 'unknown')}: {subject}"    
                                                        
                                                                                                        
@registry.tool("gmail_send", "Send an email")             
async def gmail_send(to: str, subject: str, body: str) -> str:
    svc = _get_service()
                                                                                                        
    message = MIMEText(body)
    message["to"] = to                                                                                    
    message["subject"] = subject                          

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = svc.users().messages().send(
        userId="me", body={"raw": raw}                                                                    
    ).execute()
                                                                                                        
    return f"Sent to {to}: {subject} (id: {sent['id']})" 