"""HTML parsing for page, link, image, resource, email, and social data."""

from __future__ import annotations

import re
from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import urlparse

from seo_site_scraper_pro.models.entities import ImageInfo, LinkInfo, PageData, ResourceInfo
from seo_site_scraper_pro.utils.url_tools import normalize_url, same_domain

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SOCIAL_HOSTS = {"Facebook": "facebook.com", "Instagram": "instagram.com", "X": "x.com", "LinkedIn": "linkedin.com", "YouTube": "youtube.com", "TikTok": "tiktok.com", "Pinterest": "pinterest.com", "GitHub": "github.com", "Discord": "discord.gg", "Telegram": "t.me"}


class _SEOHTMLParser(HTMLParser):
    """Small dependency-free HTML parser optimized for SEO extraction."""

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.language = ""
        self.charset = ""
        self.h1: list[str] = []
        self.h2_count = 0
        self.h3_count = 0
        self.links: list[LinkInfo] = []
        self.images: list[ImageInfo] = []
        self.resources: list[ResourceInfo] = []
        self.structured_data = False
        self.open_graph = False
        self.twitter_cards = False
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._current_link: LinkInfo | None = None
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "html":
            self.language = attr.get("lang", "")
        if tag == "title":
            self._start_capture("title")
        if tag in {"h1", "h2", "h3"}:
            self._start_capture(tag)
        if tag == "meta":
            name = attr.get("name", "").lower()
            prop = attr.get("property", "").lower()
            if name == "description":
                self.description = attr.get("content", "").strip()
            if name == "robots":
                self.robots = attr.get("content", "")
            if "charset" in attr:
                self.charset = attr["charset"]
            if prop.startswith("og:"):
                self.open_graph = True
            if name.startswith("twitter:"):
                self.twitter_cards = True
        if tag == "link" and attr.get("href"):
            rel = attr.get("rel", "").lower()
            href = normalize_url(attr["href"], self.page_url)
            if "canonical" in rel:
                self.canonical = href
            kind = "CSS" if "stylesheet" in rel else "RSS" if "alternate" in rel else "Font" if "preload" in rel else "Resource"
            self.resources.append(ResourceInfo(self.page_url, href, kind))
        if tag == "script":
            if attr.get("type") == "application/ld+json":
                self.structured_data = True
            if attr.get("src"):
                self.resources.append(ResourceInfo(self.page_url, normalize_url(attr["src"], self.page_url), "JavaScript"))
        if tag == "a" and attr.get("href") and not attr["href"].startswith(("mailto:", "tel:", "javascript:")):
            target = normalize_url(attr["href"], self.page_url)
            rel = set(attr.get("rel", "").lower().split())
            self._current_link = LinkInfo(self.page_url, target, "", same_domain(target, self.page_url), "nofollow" in rel, "sponsored" in rel, "ugc" in rel)
        if tag == "img" and attr.get("src"):
            src = attr["src"]
            self.images.append(ImageInfo(self.page_url, normalize_url(src, self.page_url), attr.get("alt", ""), self._int(attr.get("width")), self._int(attr.get("height")), format=urlparse(src).path.rsplit(".", 1)[-1].lower(), lazy_load=attr.get("loading") == "lazy"))
        if tag in {"video", "source"} and attr.get("src"):
            self.resources.append(ResourceInfo(self.page_url, normalize_url(attr["src"], self.page_url), "Video"))

    def handle_endtag(self, tag: str) -> None:
        text = " ".join(self._buffer).strip()
        if self._capture == tag:
            if tag == "title":
                self.title = text
            elif tag == "h1":
                self.h1.append(text)
            elif tag == "h2":
                self.h2_count += 1
            elif tag == "h3":
                self.h3_count += 1
            self._capture = None
            self._buffer = []
        if tag == "a" and self._current_link:
            self._current_link.anchor_text = text
            self.links.append(self._current_link)
            self._current_link = None

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if clean:
            self.text_parts.append(clean)
            if self._capture or self._current_link:
                self._buffer.append(clean)

    def _start_capture(self, tag: str) -> None:
        self._capture = tag
        self._buffer = []

    def _int(self, value: str | None) -> int | None:
        try:
            return int(value) if value else None
        except ValueError:
            return None


class PageParser:
    """Parse raw HTML into structured page data."""

    def parse(self, url: str, depth: int, html: str, headers: dict[str, str], elapsed: float, status: int) -> PageData:
        parser = _SEOHTMLParser(url)
        parser.feed(html)
        socials: dict[str, set[str]] = defaultdict(set)
        for link in parser.links:
            host = urlparse(link.target_url).hostname or ""
            for platform, domain in SOCIAL_HOSTS.items():
                if domain in host:
                    socials[platform].add(link.target_url)
        text = " ".join(parser.text_parts)
        return PageData(url=url, depth=depth, status_code=status, response_time=elapsed, content_type=headers.get("content-type", ""), page_size=len(html.encode("utf-8")), title=parser.title, title_length=len(parser.title), meta_description=parser.description, description_length=len(parser.description), h1=parser.h1, h2_count=parser.h2_count, h3_count=parser.h3_count, canonical=parser.canonical, meta_robots=parser.robots, language=parser.language, charset=parser.charset, word_count=len(re.findall(r"\w+", text)), internal_links_count=sum(1 for link in parser.links if link.is_internal), external_links_count=sum(1 for link in parser.links if not link.is_internal), image_count=len(parser.images), structured_data=parser.structured_data, open_graph=parser.open_graph, twitter_cards=parser.twitter_cards, last_modified=headers.get("last-modified", ""), server_header=headers.get("server", ""), headers=headers, links=parser.links, images=parser.images, resources=parser.resources, emails=set(EMAIL_RE.findall(html)), social_profiles=dict(socials))
