"""Domain models for SEO Site Scraper Pro."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


@dataclass(slots=True)
class CrawlSettings:
    """Runtime crawler settings from the desktop form."""

    start_url: str
    max_pages: int = 500
    max_depth: int = 3
    concurrency: int = 10
    timeout: float = 15.0
    retries: int = 2
    user_agent: str = "SEO Site Scraper Pro/1.0"
    respect_robots: bool = True
    crawl_images: bool = True
    crawl_css: bool = True
    crawl_javascript: bool = True
    crawl_pdfs: bool = True
    analyze_seo: bool = True
    find_emails: bool = True
    detect_social_media: bool = True
    check_broken_links: bool = True
    follow_redirects: bool = True
    export_report_automatically: bool = False
    export_folder: Path = Path("reports")


@dataclass(slots=True)
class LinkInfo:
    source_url: str
    target_url: str
    anchor_text: str = ""
    is_internal: bool = False
    nofollow: bool = False
    sponsored: bool = False
    ugc: bool = False
    status_code: int | None = None
    redirect_chain: list[str] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class ImageInfo:
    source_url: str
    image_url: str
    alt: str = ""
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    format: str = ""
    lazy_load: bool = False

    @property
    def missing_alt(self) -> bool:
        return not self.alt.strip()

    @property
    def large_image_warning(self) -> bool:
        return bool(self.file_size and self.file_size > 500_000)


@dataclass(slots=True)
class ResourceInfo:
    source_url: str
    resource_url: str
    resource_type: str
    status_code: int | None = None


@dataclass(slots=True)
class PageData:
    url: str
    depth: int
    status_code: int = 0
    response_time: float = 0.0
    content_type: str = ""
    page_size: int = 0
    title: str = ""
    title_length: int = 0
    meta_description: str = ""
    description_length: int = 0
    h1: list[str] = field(default_factory=list)
    h2_count: int = 0
    h3_count: int = 0
    canonical: str = ""
    meta_robots: str = ""
    language: str = ""
    charset: str = ""
    word_count: int = 0
    internal_links_count: int = 0
    external_links_count: int = 0
    image_count: int = 0
    structured_data: bool = False
    open_graph: bool = False
    twitter_cards: bool = False
    last_modified: str = ""
    server_header: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    links: list[LinkInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    resources: list[ResourceInfo] = field(default_factory=list)
    emails: set[str] = field(default_factory=set)
    social_profiles: dict[str, set[str]] = field(default_factory=dict)
    error: str = ""


@dataclass(slots=True)
class SEOIssue:
    severity: Severity
    description: str
    recommendation: str
    affected_url: str
    category: str


@dataclass(slots=True)
class CrawlResult:
    settings: CrawlSettings
    pages: dict[str, PageData] = field(default_factory=dict)
    issues: list[SEOIssue] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    resources: list[ResourceInfo] = field(default_factory=list)
    emails: set[str] = field(default_factory=set)
    social_profiles: dict[str, set[str]] = field(default_factory=dict)
    sitemap_urls: set[str] = field(default_factory=set)
    robots_txt: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    seo_score: int = 100

    def as_summary(self) -> dict[str, Any]:
        internal = sum(1 for link in self.links if link.is_internal)
        external = len(self.links) - internal
        broken = sum(1 for link in self.links if link.status_code and link.status_code >= 400)
        redirects = sum(1 for page in self.pages.values() if page.status_code in {301, 302, 307, 308})
        avg_response = 0.0
        if self.pages:
            avg_response = sum(page.response_time for page in self.pages.values()) / len(self.pages)
        return {
            "total_urls": len(self.pages),
            "internal_urls": internal,
            "external_urls": external,
            "broken_links": broken,
            "redirects": redirects,
            "images": len(self.images),
            "missing_alt": sum(1 for image in self.images if image.missing_alt),
            "missing_titles": sum(1 for page in self.pages.values() if not page.title),
            "missing_descriptions": sum(1 for page in self.pages.values() if not page.meta_description),
            "average_response_time": round(avg_response, 3),
            "seo_score": self.seo_score,
        }
