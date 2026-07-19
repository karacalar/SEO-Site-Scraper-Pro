"""Asynchronous queue-based crawler engine."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urljoin

import aiohttp

from seo_site_scraper_pro.analyzer.seo_analyzer import SEOAnalyzer
from seo_site_scraper_pro.models.entities import CrawlResult, CrawlSettings, PageData
from seo_site_scraper_pro.parser.page_parser import PageParser
from seo_site_scraper_pro.utils.url_tools import is_html_like, normalize_url, same_domain

ProgressCallback = Callable[[CrawlResult, str], None]


class AsyncCrawler:
    """Fast aiohttp crawler with pause, stop, depth, and concurrency controls."""

    def __init__(self, settings: CrawlSettings, progress_callback: ProgressCallback | None = None) -> None:
        self.settings = settings
        self.progress_callback = progress_callback
        self.result = CrawlResult(settings=settings)
        self.parser = PageParser()
        self.analyzer = SEOAnalyzer()
        self.logger = logging.getLogger(__name__)
        self._visited: set[str] = set()
        self._queued: set[str] = set()
        self._queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._pause = asyncio.Event()
        self._pause.set()

    async def crawl(self) -> CrawlResult:
        """Run the crawl and return a populated result."""

        start_url = normalize_url(self.settings.start_url)
        await self._discover_sitemaps(start_url)
        await self._enqueue(start_url, 0)
        timeout = aiohttp.ClientTimeout(total=self.settings.timeout)
        connector = aiohttp.TCPConnector(limit=self.settings.concurrency, ttl_dns_cache=300)
        headers = {"User-Agent": self.settings.user_agent}
        async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
            workers = [asyncio.create_task(self._worker(session)) for _ in range(self.settings.concurrency)]
            await self._queue.join()
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        self.analyzer.analyze(self.result)
        self.result.completed_at = datetime.now(UTC)
        self._emit("Crawl complete")
        return self.result

    def stop(self) -> None:
        """Request crawler shutdown."""

        self._stop.set()

    def pause(self) -> None:
        """Pause workers."""

        self._pause.clear()

    def resume(self) -> None:
        """Resume workers."""

        self._pause.set()

    async def _worker(self, session: aiohttp.ClientSession) -> None:
        while not self._stop.is_set():
            await self._pause.wait()
            url, depth = await self._queue.get()
            try:
                if url not in self._visited and len(self._visited) < self.settings.max_pages:
                    await self._fetch_page(session, url, depth)
            finally:
                self._queue.task_done()

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str, depth: int) -> None:
        self._visited.add(url)
        started = perf_counter()
        try:
            async with session.get(url, allow_redirects=self.settings.follow_redirects) as response:
                body = await response.read()
                elapsed = perf_counter() - started
                headers = {key.lower(): value for key, value in response.headers.items()}
                content_type = headers.get("content-type", "")
                if "text/html" not in content_type:
                    page = PageData(url=url, depth=depth, status_code=response.status, response_time=elapsed, content_type=content_type, page_size=len(body), headers=headers)
                else:
                    html = body.decode(response.charset or "utf-8", errors="replace")
                    page = self.parser.parse(str(response.url), depth, html, headers, elapsed, response.status)
                    await self._queue_links(page, depth)
                self._merge_page(page)
                self._emit(f"Crawled {url} ({response.status})")
        except (aiohttp.ClientError, TimeoutError, UnicodeError) as exc:
            self.logger.warning("Failed to crawl %s: %s", url, exc)
            self.result.pages[url] = PageData(url=url, depth=depth, status_code=0)
            self._emit(f"Error crawling {url}: {exc}")

    async def _queue_links(self, page: PageData, depth: int) -> None:
        if depth >= self.settings.max_depth:
            return
        for link in page.links:
            if link.is_internal and is_html_like(link.target_url):
                await self._enqueue(link.target_url, depth + 1)

    async def _enqueue(self, url: str, depth: int) -> None:
        if url in self._queued or len(self._queued) >= self.settings.max_pages:
            return
        if not same_domain(url, self.settings.start_url):
            return
        self._queued.add(url)
        await self._queue.put((url, depth))

    def _merge_page(self, page: PageData) -> None:
        self.result.pages[page.url] = page
        self.result.links.extend(page.links)
        self.result.images.extend(page.images)
        self.result.resources.extend(page.resources)
        self.result.emails.update(page.emails)
        for platform, urls in page.social_profiles.items():
            self.result.social_profiles.setdefault(platform, set()).update(urls)

    async def _discover_sitemaps(self, start_url: str) -> None:
        parsed_root = f"{urljoin(start_url, '/')}"
        self.result.sitemap_urls.update({urljoin(parsed_root, "sitemap.xml"), urljoin(parsed_root, "sitemap_index.xml")})
        self.result.robots_txt = urljoin(parsed_root, "robots.txt")

    def _emit(self, message: str) -> None:
        self.logger.info(message)
        if self.progress_callback:
            self.progress_callback(self.result, message)
