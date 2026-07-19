"""Multi-page CustomTkinter views for the desktop navigation shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.models.entities import CrawlResult


class BasePageFrame(ctk.CTkFrame):
    """Base class for content pages managed by PageManager."""

    def refresh(self, result: CrawlResult | None) -> None:
        """Refresh page content from the current crawl result."""


class TextPageFrame(BasePageFrame):
    """Reusable page with a title, helper text, and text/table content."""

    def __init__(self, parent: ctk.CTkFrame, title: str, subtitle: str) -> None:
        super().__init__(parent, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 2)
        )
        ctk.CTkLabel(self, text=subtitle, text_color="#a3a3a3", anchor="w").grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 12)
        )
        self.textbox = ctk.CTkTextbox(self, wrap="none")
        self.textbox.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._write("Run a scan to populate this page.")

    def refresh(self, result: CrawlResult | None) -> None:
        if result is None:
            self._write("Run a scan to populate this page.")

    def _write(self, content: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", content)
        self.textbox.configure(state="disabled")


class DashboardFrame(BasePageFrame):
    """Dashboard overview with cards, progress, and crawl statistics."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 10)
        )
        self.card_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.card_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.cards: dict[str, ctk.CTkLabel] = {}
        metrics = [
            "Total URLs", "Internal URLs", "External URLs", "Broken Links", "Redirects", "Images",
            "Missing ALT", "Missing Titles", "Missing Descriptions", "Average Response Time", "SEO Score",
        ]
        for index, metric in enumerate(metrics):
            self.card_frame.grid_columnconfigure(index % 6, weight=1)
            card = ctk.CTkFrame(self.card_frame)
            card.grid(row=index // 6, column=index % 6, sticky="ew", padx=6, pady=6)
            ctk.CTkLabel(card, text=metric, text_color="#a3a3a3").pack(padx=12, pady=(8, 0))
            value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=20, weight="bold"))
            value.pack(padx=12, pady=(0, 8))
            self.cards[metric] = value
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.progress.set(0)
        self.details = ctk.CTkTextbox(self, wrap="none")
        self.details.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.details.insert("1.0", "Live crawl status and top issues will appear here.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            for card in self.cards.values():
                card.configure(text="0")
            self.progress.set(0)
            self.details.delete("1.0", "end")
            self.details.insert("1.0", "Live crawl status and top issues will appear here.")
            return
        summary = result.as_summary()
        labels = {
            "Total URLs": "total_urls", "Internal URLs": "internal_urls", "External URLs": "external_urls",
            "Broken Links": "broken_links", "Redirects": "redirects", "Images": "images",
            "Missing ALT": "missing_alt", "Missing Titles": "missing_titles",
            "Missing Descriptions": "missing_descriptions", "Average Response Time": "average_response_time",
            "SEO Score": "seo_score",
        }
        for label, key in labels.items():
            self.cards[label].configure(text=str(summary[key]))
        self.progress.set(min(1.0, len(result.pages) / max(1, result.settings.max_pages)))
        top = result.issues[:10]
        lines = ["Top SEO Issues", "Severity\tCategory\tURL\tRecommendation"]
        lines.extend(f"{i.severity.value}\t{i.category}\t{i.affected_url}\t{i.recommendation}" for i in top)
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines) if top else "No SEO issues detected yet.")


class PagesFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame, search_getter: Callable[[], str]) -> None:
        self.search_getter = search_getter
        super().__init__(parent, "Pages", "Crawled pages with searchable URL, title, status, and depth data.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        term = self.search_getter().lower()
        lines = ["URL\tStatus\tDepth\tTitle\tH1\tWords\tResponse Time"]
        for page in result.pages.values():
            line = f"{page.url}\t{page.status_code}\t{page.depth}\t{page.title}\t{len(page.h1)}\t{page.word_count}\t{page.response_time:.3f}s"
            if not term or term in line.lower():
                lines.append(line)
        self._write("\n".join(lines))


class SEOFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "SEO Analysis", "Issues grouped by severity with recommendations.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        lines = ["Severity\tCategory\tAffected URL\tDescription\tRecommendation"]
        lines.extend(f"{i.severity.value}\t{i.category}\t{i.affected_url}\t{i.description}\t{i.recommendation}" for i in result.issues)
        self._write("\n".join(lines))


class ImagesFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Images", "Image inventory, missing ALT text, and large image warnings.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        lines = ["Image URL\tSource URL\tALT\tWidth\tHeight\tMissing ALT\tLarge"]
        lines.extend(f"{img.image_url}\t{img.source_url}\t{img.alt}\t{img.width or ''}\t{img.height or ''}\t{img.missing_alt}\t{img.large_image_warning}" for img in result.images)
        self._write("\n".join(lines))


class LinksFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Links", "Internal, external, broken, and redirected links.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        lines = ["Target URL\tSource URL\tType\tStatus\tAnchor\tNofollow\tRedirect Chain"]
        lines.extend(f"{l.target_url}\t{l.source_url}\t{'Internal' if l.is_internal else 'External'}\t{l.status_code or ''}\t{l.anchor_text}\t{l.nofollow}\t{' > '.join(l.redirect_chain)}" for l in result.links)
        self._write("\n".join(lines))


class ResourcesFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Resources", "CSS, JavaScript, fonts, PDFs, XML, RSS, and media resources.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        lines = ["Type\tResource URL\tSource URL\tStatus"]
        lines.extend(f"{r.resource_type}\t{r.resource_url}\t{r.source_url}\t{r.status_code or ''}" for r in result.resources)
        self._write("\n".join(lines))


class EmailsFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Emails", "Unique public email addresses discovered during the crawl.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        self._write("\n".join(sorted(result.emails)) or "No email addresses detected.")


class SocialMediaFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Social Media", "Detected social media profiles grouped by network.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        lines = ["Network\tProfile URL"]
        for network, urls in sorted(result.social_profiles.items()):
            lines.extend(f"{network}\t{url}" for url in sorted(urls))
        self._write("\n".join(lines))


class SecurityFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Security", "HTTPS and security header overview for crawled pages.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        headers = ["strict-transport-security", "content-security-policy", "x-frame-options", "x-xss-protection", "referrer-policy", "permissions-policy", "server", "x-powered-by"]
        lines = ["URL\tHTTPS\t" + "\t".join(headers)]
        for page in result.pages.values():
            lower_headers = {key.lower(): value for key, value in page.headers.items()}
            values = [lower_headers.get(header, "") for header in headers]
            lines.append(f"{page.url}\t{page.url.startswith('https://')}\t" + "\t".join(values))
        self._write("\n".join(lines))


class SitemapsFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Sitemaps", "Detected sitemap URLs from standard locations and robots.txt.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        self._write("\n".join(sorted(result.sitemap_urls)) or "No sitemap URLs detected.")


class RobotsFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Robots.txt", "Raw robots.txt content discovered for the website.")

    def refresh(self, result: CrawlResult | None) -> None:
        if not result:
            super().refresh(result)
            return
        self._write(result.robots_txt or "No robots.txt content detected.")


class ExportFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, "Export", "Use the toolbar Export button to generate Excel, CSV, JSON, and HTML reports.")

    def refresh(self, result: CrawlResult | None) -> None:
        count = len(result.pages) if result else 0
        self._write(f"Ready to export {count} crawled pages.\nFormats: Excel (.xlsx), CSV, JSON, Professional HTML Report")


class SettingsFrame(TextPageFrame):
    def __init__(self, parent: ctk.CTkFrame, settings_getter: Callable[[], dict[str, Any]]) -> None:
        self.settings_getter = settings_getter
        super().__init__(parent, "Settings", "Current theme, concurrency, timeout, user agent, and export folder.")

    def refresh(self, result: CrawlResult | None) -> None:
        settings = self.settings_getter()
        self._write("\n".join(f"{key}: {value}" for key, value in settings.items()))


class PageManager:
    """Register, hide, and show CTkFrame pages without recreating the window."""

    def __init__(self, container: ctk.CTkFrame) -> None:
        self.container = container
        self.pages: dict[str, BasePageFrame] = {}
        self.active_page: str = ""

    def register(self, name: str, page: BasePageFrame) -> None:
        self.pages[name] = page
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_remove()

    def show(self, name: str) -> None:
        if name not in self.pages:
            raise KeyError(f"Page is not registered: {name}")
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid()
            else:
                page.grid_remove()
        self.active_page = name

    def refresh_all(self, result: CrawlResult | None) -> None:
        for page in self.pages.values():
            page.refresh(result)
