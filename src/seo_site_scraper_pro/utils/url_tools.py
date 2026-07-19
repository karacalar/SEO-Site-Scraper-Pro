"""URL normalization and classification helpers."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse, urlunparse


def normalize_url(url: str, base_url: str | None = None) -> str:
    """Return a normalized absolute HTTP(S) URL without fragments."""

    absolute = urljoin(base_url, url) if base_url else url
    absolute, _ = urldefrag(absolute.strip())
    parsed = urlparse(absolute)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def same_domain(url: str, root_url: str) -> bool:
    """Return whether two URLs share a hostname, ignoring a leading www."""

    left = urlparse(url).hostname or ""
    right = urlparse(root_url).hostname or ""
    return left.removeprefix("www.") == right.removeprefix("www.")


def is_html_like(url: str) -> bool:
    """Return whether a URL probably points to an HTML page."""

    path = urlparse(url).path.lower()
    return not path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".pdf", ".zip"))
