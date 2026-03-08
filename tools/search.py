# tools/search.py
from ddgs import DDGS
import urllib.request
import urllib.error
import re

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return results as a formatted string
    ready to be injected into the LLM prompt.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No results found."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r['title']}\n{r['body']}\nSource: {r['href']}")

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Search failed: {str(e)}"

def fetch_page(url: str, max_chars: int = 3000) -> str:
    """
    Fetch the actual content of a webpage and return clean readable text.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # strip script and style tags entirely
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>',   '', html, flags=re.DOTALL)

        # strip all remaining html tags
        text = re.sub(r'<[^>]+>', ' ', html)

        # decode common html entities
        text = text.replace('&amp;',  '&')
        text = text.replace('&lt;',   '<')
        text = text.replace('&gt;',   '>')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&#39;',  "'")
        text = text.replace('&quot;', '"')

        # collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # truncate to max_chars so we don't blow up the context window
        if len(text) > max_chars:
            text = text[:max_chars] + "... (truncated)"

        return text

    except Exception as e:
        return f"Could not fetch page: {str(e)}"