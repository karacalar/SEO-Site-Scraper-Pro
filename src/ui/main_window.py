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
from src.ui.pages import (
    DashboardFrame,
    EmailsFrame,
    ExportFrame,
    ImagesFrame,
    LinksFrame,
    PageManager,
    PagesFrame,
    ResourcesFrame,
    RobotsFrame,
    SEOFrame,
    SecurityFrame,
    SettingsFrame,
    SitemapsFrame,
    SocialMediaFrame,
)


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
        self.sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="SEO Site\nScraper Pro", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=24)
        for section in self._section_names():
            button = ctk.CTkButton(
                self.sidebar,
                text=section,
                anchor="w",
                fg_color="transparent",
                command=lambda name=section: self._show_section(name),
            )
            button.pack(fill="x", padx=14, pady=4)
            self.sidebar_buttons[section] = button
        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        self._build_toolbar()
        self._build_pages()
        self._build_status_bar()
        self._show_section("Dashboard")

    def _section_names(self) -> list[str]:
        return [
            "Dashboard", "Pages", "SEO Analysis", "Images", "Links", "Resources", "Emails",
            "Social Media", "Security", "Sitemaps", "Robots.txt", "Export", "Settings",
        ]

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
        self.search_entry.bind("<KeyRelease>", lambda _event: self._refresh_pages())

    def _entry(self, parent: ctk.CTkFrame, placeholder: str, value: str, row: int, column: int, span: int = 1) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        entry.insert(0, value)
        entry.grid(row=row, column=column, columnspan=span, sticky="ew", padx=8, pady=8)
        return entry

    def _build_pages(self) -> None:
        self.page_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_container.grid(row=1, column=0, sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_manager = PageManager(self.page_container)
        self.page_manager.register("Dashboard", DashboardFrame(self.page_container))
        self.page_manager.register("Pages", PagesFrame(self.page_container, lambda: self.search_entry.get()))
        self.page_manager.register("SEO Analysis", SEOFrame(self.page_container))
        self.page_manager.register("Images", ImagesFrame(self.page_container))
        self.page_manager.register("Links", LinksFrame(self.page_container))
        self.page_manager.register("Resources", ResourcesFrame(self.page_container))
        self.page_manager.register("Emails", EmailsFrame(self.page_container))
        self.page_manager.register("Social Media", SocialMediaFrame(self.page_container))
        self.page_manager.register("Security", SecurityFrame(self.page_container))
        self.page_manager.register("Sitemaps", SitemapsFrame(self.page_container))
        self.page_manager.register("Robots.txt", RobotsFrame(self.page_container))
        self.page_manager.register("Export", ExportFrame(self.page_container))
        self.page_manager.register("Settings", SettingsFrame(self.page_container, self._current_settings_summary))

    def _build_status_bar(self) -> None:
        self.status_label = ctk.CTkLabel(self.content, text="Ready", anchor="w")
        self.status_label.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _current_settings_summary(self) -> dict[str, str]:
        return {
            "Theme": ctk.get_appearance_mode(),
            "Concurrent Requests": self.concurrency_entry.get(),
            "Timeout": self.timeout_entry.get(),
            "User Agent": self.user_agent_entry.get(),
            "Export Folder": str(self.export_folder),
        }

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
        self._refresh_pages()
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
            self._refresh_pages()
        self.after(200, self._poll_events)

    def _refresh_pages(self) -> None:
        self.page_manager.refresh_all(self.result)

    def _show_section(self, section: str) -> None:
        self.page_manager.show(section)
        for name, button in self.sidebar_buttons.items():
            button.configure(fg_color=("#1f6aa5" if name == section else "transparent"))
        self._refresh_pages()
        self._set_status(f"Viewing {section}")

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=f"Status: {message}")
