"""URL validation, normalization, and classification helpers."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse, urlunparse


def ensure_scheme(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def normalize_url(url: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url, url) if base_url else ensure_scheme(url)
    absolute, _fragment = urldefrag(absolute.strip())
    parsed = urlparse(absolute)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def same_domain(url: str, root_url: str) -> bool:
    left = urlparse(url).hostname or ""
    right = urlparse(root_url).hostname or ""
    return left.removeprefix("www.") == right.removeprefix("www.")


def is_html_like(url: str) -> bool:
    path = urlparse(url).path.lower()
    blocked = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".pdf", ".zip")
    return not path.endswith(blocked)
