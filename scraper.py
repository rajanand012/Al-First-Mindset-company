"""Web scraper with 7-day caching for company website content."""

import hashlib
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from database import get_cached_content, set_cached_content

USER_AGENT = (
    "Mozilla/5.0 (compatible; AI-Mindset-Assessor/1.0; "
    "+https://github.com/al-first-mindset)"
)
REQUEST_TIMEOUT = 15
MAX_CONTENT_LENGTH = 50_000  # chars per page


def fetch_website(url):
    """Fetch website content, using cache if available within 7 days.

    Returns dict with 'text', 'title', 'pages', and 'content_hash'.
    """
    # Normalise URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    cached = get_cached_content(url)
    if cached:
        content_hash = hashlib.sha256(cached.encode()).hexdigest()[:16]
        return {
            "text": cached,
            "content_hash": content_hash,
            "from_cache": True,
        }

    # Fetch homepage + key subpages
    pages_to_check = [
        url,
        urljoin(url, "/about"),
        urljoin(url, "/about-us"),
        urljoin(url, "/technology"),
        urljoin(url, "/innovation"),
        urljoin(url, "/products"),
        urljoin(url, "/solutions"),
        urljoin(url, "/services"),
    ]

    all_text = []
    for page_url in pages_to_check:
        text = _fetch_page(page_url)
        if text:
            all_text.append(f"--- PAGE: {page_url} ---\n{text}")

    combined = "\n\n".join(all_text)
    if not combined.strip():
        raise ValueError(
            f"Could not fetch any content from {url}. "
            "Please check the URL and try again."
        )

    # Truncate to stay within reasonable limits
    if len(combined) > MAX_CONTENT_LENGTH * 4:
        combined = combined[: MAX_CONTENT_LENGTH * 4]

    # Cache the result
    set_cached_content(url, combined)

    content_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
    return {
        "text": combined,
        "content_hash": content_hash,
        "from_cache": False,
    }


def _fetch_page(url):
    """Fetch and extract readable text from a single page."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text[:MAX_CONTENT_LENGTH] if text.strip() else None

    except (requests.RequestException, Exception):
        return None
