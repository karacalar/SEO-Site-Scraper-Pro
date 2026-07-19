"""CustomTkinter main window for SEO Site Scraper Pro."""

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.crawler.crawler import WebsiteCrawler
from src.exporters.exporter import ReportExporter
from src.models.entities import CrawlResult, CrawlSettings


class MainWindow(ctk.CTk):
    """Professional dark desktop application shell."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("SEO Site Scraper Pro")
        self.geometry("1480x920")
        self.minsize(1180, 760)
        self.events: queue.Queue[tuple[CrawlResult | None, str]] = queue.Queue()
        self.crawler: WebsiteCrawler | None = None
        self.result: CrawlResult | None = None
        self.export_folder = Path("reports")
        self._build_layout()
        self.after(200, self._poll_events)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="SEO Site\nScraper Pro", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=24)
        for section in ["Dashboard", "Pages", "SEO Analysis", "Images", "Links", "Resources", "Emails", "Social Media", "Security", "Sitemaps", "Robots.txt", "Export", "Settings"]:
            ctk.CTkButton(self.sidebar, text=section, anchor="w", command=lambda name=section: self._show_section(name)).pack(fill="x", padx=14, pady=4)
        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(3, weight=1)
        self._build_toolbar()
        self._build_dashboard()
        self._build_results()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self.content)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index in range(8):
            toolbar.grid_columnconfigure(index, weight=1)
        self.url_entry = self._entry(toolbar, "Website URL", "https://example.com", 0, 0, 3)
        self.max_pages_entry = self._entry(toolbar, "Maximum Pages", "100", 0, 3)
        self.max_depth_entry = self._entry(toolbar, "Maximum Depth", "3", 0, 4)
        self.concurrency_entry = self._entry(toolbar, "Concurrent Requests", "10", 0, 5)
        self.timeout_entry = self._entry(toolbar, "Timeout", "15", 0, 6)
        self.user_agent_entry = self._entry(toolbar, "User Agent", "SEO Site Scraper Pro/1.0", 0, 7)
        self.checkboxes: dict[str, ctk.CTkCheckBox] = {}
        labels = ["Crawl Images", "Crawl CSS", "Crawl JavaScript", "Crawl PDFs", "Analyze SEO", "Find Emails", "Detect Social Media", "Check Broken Links", "Follow Redirects", "Respect Robots", "Export Report Automatically"]
        for index, label in enumerate(labels):
            box = ctk.CTkCheckBox(toolbar, text=label)
            box.select()
            box.grid(row=1 + index // 6, column=index % 6, sticky="w", padx=8, pady=6)
            self.checkboxes[label] = box
        buttons = [("Start Scan", self.start_scan), ("Stop", self.stop_scan), ("Pause", self.pause_scan), ("Resume", self.resume_scan), ("Clear", self.clear_results), ("Export", self.export_results), ("Export Folder", self.choose_export_folder)]
        for index, (label, command) in enumerate(buttons):
            ctk.CTkButton(toolbar, text=label, command=command).grid(row=3, column=index, sticky="ew", padx=8, pady=10)
        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="Global search: URL, title, status, issue, depth")
        self.search_entry.grid(row=3, column=7, sticky="ew", padx=8, pady=10)
        self.search_entry.bind("<KeyRelease>", lambda _event: self._refresh_results())

    def _entry(self, parent: ctk.CTkFrame, placeholder: str, value: str, row: int, column: int, span: int = 1) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        entry.insert(0, value)
        entry.grid(row=row, column=column, columnspan=span, sticky="ew", padx=8, pady=8)
        return entry

    def _build_dashboard(self) -> None:
        self.dashboard = ctk.CTkFrame(self.content)
        self.dashboard.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.cards: dict[str, ctk.CTkLabel] = {}
        metrics = ["Total URLs", "Internal URLs", "External URLs", "Broken Links", "Redirects", "Images", "Missing ALT", "Missing Titles", "Missing Descriptions", "Average Response Time", "SEO Score"]
        for index, metric in enumerate(metrics):
            card = ctk.CTkFrame(self.dashboard)
            card.grid(row=index // 6, column=index % 6, sticky="ew", padx=6, pady=6)
            ctk.CTkLabel(card, text=metric, text_color="#a3a3a3").pack(padx=12, pady=(8, 0))
            value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=20, weight="bold"))
            value.pack(padx=12, pady=(0, 8))
            self.cards[metric] = value
        self.progress = ctk.CTkProgressBar(self.content)
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.progress.set(0)

    def _build_results(self) -> None:
        self.results_box = ctk.CTkTextbox(self.content, wrap="none")
        self.results_box.grid(row=3, column=0, sticky="nsew")

    def _build_status_bar(self) -> None:
        self.status_label = ctk.CTkLabel(self.content, text="Ready", anchor="w")
        self.status_label.grid(row=4, column=0, sticky="ew", pady=(8, 0))

    def start_scan(self) -> None:
        try:
            settings = CrawlSettings(
                start_url=self.url_entry.get(),
                max_pages=max(1, int(self.max_pages_entry.get())),
                max_depth=max(0, int(self.max_depth_entry.get())),
                concurrency=max(1, int(self.concurrency_entry.get())),
                timeout=max(1.0, float(self.timeout_entry.get())),
                user_agent=self.user_agent_entry.get() or "SEO Site Scraper Pro/1.0",
                respect_robots=self.checkboxes["Respect Robots"].get() == 1,
                follow_redirects=self.checkboxes["Follow Redirects"].get() == 1,
                check_broken_links=self.checkboxes["Check Broken Links"].get() == 1,
                export_report_automatically=self.checkboxes["Export Report Automatically"].get() == 1,
                export_folder=self.export_folder,
            )
        except ValueError:
            messagebox.showerror("Invalid settings", "Maximum pages, depth, concurrency, and timeout must be valid numbers.")
            return
        self.crawler = WebsiteCrawler(settings, lambda result, message: self.events.put((result, message)))
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
        self.results_box.delete("1.0", "end")
        self.progress.set(0)
        for card in self.cards.values():
            card.configure(text="0")
        self._set_status("Results cleared")

    def export_results(self) -> None:
        if not self.result:
            messagebox.showinfo("No results", "Run a scan before exporting reports.")
            return
        paths = ReportExporter(self.export_folder).export_all(self.result)
        messagebox.showinfo("Export complete", "Reports saved:\n" + "\n".join(str(path) for path in paths.values()))

    def choose_export_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(self.export_folder))
        if folder:
            self.export_folder = Path(folder)
            self._set_status(f"Export folder set to {self.export_folder}")

    def _poll_events(self) -> None:
        while not self.events.empty():
            result, message = self.events.get_nowait()
            self.result = result or self.result
            self._set_status(message)
            self._refresh_dashboard()
            self._refresh_results()
        self.after(200, self._poll_events)

    def _refresh_dashboard(self) -> None:
        if not self.result:
            return
        summary = self.result.as_summary()
        labels = {
            "Total URLs": "total_urls",
            "Internal URLs": "internal_urls",
            "External URLs": "external_urls",
            "Broken Links": "broken_links",
            "Redirects": "redirects",
            "Images": "images",
            "Missing ALT": "missing_alt",
            "Missing Titles": "missing_titles",
            "Missing Descriptions": "missing_descriptions",
            "Average Response Time": "average_response_time",
            "SEO Score": "seo_score",
        }
        for label, key in labels.items():
            self.cards[label].configure(text=str(summary[key]))
        self.progress.set(min(1.0, len(self.result.pages) / max(1, self.result.settings.max_pages)))

    def _refresh_results(self) -> None:
        if not self.result:
            return
        term = self.search_entry.get().lower()
        lines = ["URL\tStatus\tDepth\tTitle\tIssues"]
        for page in self.result.pages.values():
            issue_count = sum(1 for issue in self.result.issues if issue.affected_url == page.url)
            line = f"{page.url}\t{page.status_code}\t{page.depth}\t{page.title}\t{issue_count}"
            if not term or term in line.lower():
                lines.append(line)
        self.results_box.delete("1.0", "end")
        self.results_box.insert("1.0", "\n".join(lines))

    def _show_section(self, section: str) -> None:
        self._set_status(f"Viewing {section}")
        self._refresh_results()

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=f"Status: {message}")
