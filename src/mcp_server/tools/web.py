from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request

from mcp_server.tools.registry import registry

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Scrollkeep/1.0; "
        "+https://github.com/scrollkeep)"
    ),
}


def _strip_html(raw: str) -> str:
    """Naive HTML tag stripper."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@registry.tool(
    "web_fetch",
    "Fetch a URL and return its text content. "
    "Strips HTML tags if the response is HTML.",
)
async def web_fetch(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type:
            raw = _strip_html(raw)
        return str(raw[:10000])
    except urllib.error.URLError as e:
        return f"Error fetching URL: {e}"
    except Exception as e:
        return f"Error: {e}"


@registry.tool(
    "web_search",
    "Search the web using DuckDuckGo. Returns a list of results "
    "with titles and URLs.",
)
async def web_search(query: str) -> str:
    encoded = urllib.parse.urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{encoded}"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error searching: {e}"

    # Parse result links from DDG HTML
    results: list[str] = []
    for match in re.finditer(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        raw,
        re.DOTALL,
    ):
        link = match.group(1)
        title = _strip_html(match.group(2))
        # DDG wraps links in a redirect; extract actual URL
        if "uddg=" in link:
            parsed = urllib.parse.parse_qs(
                urllib.parse.urlparse(link).query
            )
            actual = parsed.get("uddg", [link])[0]
        else:
            actual = link
        results.append(f"- [{title}]({actual})")
        if len(results) >= 8:
            break

    if not results:
        return f"No results found for '{query}'."
    return "\n".join(results)
