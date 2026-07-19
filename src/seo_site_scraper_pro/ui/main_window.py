"""CustomTkinter desktop interface for SEO Site Scraper Pro."""

from __future__ import annotations

import asyncio
import queue
import threading
import customtkinter as ctk

from seo_site_scraper_pro.crawler.engine import AsyncCrawler
from seo_site_scraper_pro.exporters.report_exporter import ReportExporter
from seo_site_scraper_pro.models.entities import CrawlResult, CrawlSettings


class MainWindow(ctk.CTk):
    """Main application window with controls, navigation, dashboard, and results."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("SEO Site Scraper Pro")
        self.geometry("1440x900")
        self.minsize(1180, 720)
        self.events: queue.Queue[tuple[CrawlResult | None, str]] = queue.Queue()
        self.crawler: AsyncCrawler | None = None
        self.result: CrawlResult | None = None
        self._build_layout()
        self.after(250, self._poll_events)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=190, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="SEO Scraper Pro", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=24)
        for item in ["Dashboard", "Pages", "SEO Issues", "Images", "Links", "Resources", "Emails", "Social Media", "Security", "Sitemaps", "Robots.txt", "Exports", "Settings"]:
            ctk.CTkButton(self.sidebar, text=item, anchor="w", command=lambda name=item: self._set_status(f"Viewing {name}")).pack(fill="x", padx=14, pady=4)
        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(2, weight=1)
        self._build_start_panel()
        self._build_dashboard()
        self._build_results()

    def _build_start_panel(self) -> None:
        panel = ctk.CTkFrame(self.content)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for idx in range(8):
            panel.grid_columnconfigure(idx, weight=1)
        self.url = ctk.CTkEntry(panel, placeholder_text="Website URL")
        self.url.insert(0, "https://example.com")
        self.url.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.max_pages = self._entry(panel, "Maximum Pages", "100", 0, 3)
        self.max_depth = self._entry(panel, "Maximum Crawl Depth", "3", 0, 4)
        self.concurrency = self._entry(panel, "Concurrent Requests", "10", 0, 5)
        self.timeout = self._entry(panel, "Request Timeout", "15", 0, 6)
        self.agent = self._entry(panel, "User Agent", "SEO Site Scraper Pro/1.0", 0, 7)
        self.checks: dict[str, ctk.CTkCheckBox] = {}
        options = ["Crawl Images", "Crawl CSS", "Crawl JavaScript", "Crawl PDFs", "Analyze SEO", "Find Emails", "Detect Social Media", "Check Broken Links", "Follow Redirects", "Export Report Automatically"]
        for idx, text in enumerate(options):
            box = ctk.CTkCheckBox(panel, text=text)
            box.select()
            box.grid(row=1 + idx // 5, column=idx % 5, sticky="w", padx=10, pady=6)
            self.checks[text] = box
        for idx, (text, command) in enumerate([("Start Scan", self.start_scan), ("Stop Scan", self.stop_scan), ("Pause", self.pause_scan), ("Resume", self.resume_scan), ("Clear Results", self.clear_results)]):
            ctk.CTkButton(panel, text=text, command=command).grid(row=3, column=idx, sticky="ew", padx=10, pady=10)
        self.search = ctk.CTkEntry(panel, placeholder_text="Global search: URL, title, status, issue, depth")
        self.search.grid(row=3, column=5, columnspan=3, sticky="ew", padx=10, pady=10)
        self.search.bind("<KeyRelease>", lambda _event: self._refresh_results())

    def _entry(self, parent: ctk.CTkFrame, placeholder: str, value: str, row: int, column: int) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        entry.insert(0, value)
        entry.grid(row=row, column=column, sticky="ew", padx=10, pady=10)
        return entry

    def _build_dashboard(self) -> None:
        self.dashboard = ctk.CTkFrame(self.content)
        self.dashboard.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.cards: dict[str, ctk.CTkLabel] = {}
        metrics = ["Total URLs", "Internal URLs", "External URLs", "Broken Links", "Redirects", "Images", "Missing ALT", "Missing Titles", "Missing Descriptions", "Duplicate Titles", "Duplicate Descriptions", "Pages Without H1", "Canonical Errors", "Average Response Time", "HTTP Status Distribution", "SEO Score"]
        for idx, metric in enumerate(metrics):
            card = ctk.CTkFrame(self.dashboard)
            card.grid(row=idx // 8, column=idx % 8, sticky="ew", padx=6, pady=6)
            ctk.CTkLabel(card, text=metric, text_color="#9ca3af").pack(padx=10, pady=(8, 0))
            label = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=18, weight="bold"))
            label.pack(padx=10, pady=(0, 8))
            self.cards[metric] = label
        self.progress = ctk.CTkProgressBar(self.content)
        self.progress.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.progress.set(0)
        self.status = ctk.CTkLabel(self.content, text="Ready", anchor="w")
        self.status.grid(row=4, column=0, sticky="ew")

    def _build_results(self) -> None:
        self.results = ctk.CTkTextbox(self.content, wrap="none")
        self.results.grid(row=2, column=0, sticky="nsew")

    def start_scan(self) -> None:
        settings = CrawlSettings(self.url.get(), int(self.max_pages.get()), int(self.max_depth.get()), int(self.concurrency.get()), float(self.timeout.get()), self.agent.get(), export_report_automatically=self.checks["Export Report Automatically"].get() == 1)
        self.crawler = AsyncCrawler(settings, lambda result, message: self.events.put((result, message)))
        threading.Thread(target=lambda: asyncio.run(self._run_crawl()), daemon=True).start()
        self._set_status("Scan started")

    async def _run_crawl(self) -> None:
        if not self.crawler:
            return
        result = await self.crawler.crawl()
        if result.settings.export_report_automatically:
            ReportExporter(result.settings.export_folder).export_all(result)
        self.events.put((result, "Scan finished"))

    def stop_scan(self) -> None:
        if self.crawler:
            self.crawler.stop()
        self._set_status("Stop requested")

    def pause_scan(self) -> None:
        if self.crawler:
            self.crawler.pause()
        self._set_status("Paused")

    def resume_scan(self) -> None:
        if self.crawler:
            self.crawler.resume()
        self._set_status("Running")

    def clear_results(self) -> None:
        self.result = None
        self.results.delete("1.0", "end")
        self.progress.set(0)
        self._set_status("Results cleared")

    def _poll_events(self) -> None:
        while not self.events.empty():
            result, message = self.events.get_nowait()
            self.result = result or self.result
            self._set_status(message)
            self._refresh_dashboard()
            self._refresh_results()
        self.after(250, self._poll_events)

    def _refresh_dashboard(self) -> None:
        if not self.result:
            return
        summary = self.result.as_summary()
        mapping = {"Total URLs": "total_urls", "Internal URLs": "internal_urls", "External URLs": "external_urls", "Broken Links": "broken_links", "Redirects": "redirects", "Images": "images", "Missing ALT": "missing_alt", "Missing Titles": "missing_titles", "Missing Descriptions": "missing_descriptions", "Average Response Time": "average_response_time", "SEO Score": "seo_score"}
        for label, key in mapping.items():
            self.cards[label].configure(text=str(summary[key]))
        self.cards["HTTP Status Distribution"].configure(text=str({p.status_code: sum(1 for x in self.result.pages.values() if x.status_code == p.status_code) for p in self.result.pages.values()}))
        self.progress.set(min(1.0, len(self.result.pages) / max(1, self.result.settings.max_pages)))

    def _refresh_results(self) -> None:
        if not self.result:
            return
        term = self.search.get().lower()
        lines = ["URL\tStatus\tDepth\tTitle\tIssues"]
        for page in self.result.pages.values():
            issue_count = sum(1 for issue in self.result.issues if issue.affected_url == page.url)
            line = f"{page.url}\t{page.status_code}\t{page.depth}\t{page.title}\t{issue_count}"
            if not term or term in line.lower():
                lines.append(line)
        self.results.delete("1.0", "end")
        self.results.insert("1.0", "\n".join(lines))

    def _set_status(self, text: str) -> None:
        self.status.configure(text=f"Live Crawl Status: {text}")
