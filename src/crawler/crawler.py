"""Async website crawler using aiohttp and an internal queue."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import aiohttp

from src.analyzer.analyzer import SEOAnalyzer
from src.models.entities import CrawlResult, CrawlSettings, PageData
from src.parser.page_parser import PageParser
from src.utils.url_tools import is_html_like, normalize_url, same_domain

ProgressCallback = Callable[[CrawlResult, str], None]


class WebsiteCrawler:
    """Concurrent, pausable, stoppable crawler for one website."""

    def __init__(self, settings: CrawlSettings, progress_callback: ProgressCallback | None = None) -> None:
        self.settings = settings
        self.progress_callback = progress_callback
        self.result = CrawlResult(settings=settings)
        self.parser = PageParser()
        self.analyzer = SEOAnalyzer()
        self.logger = logging.getLogger(__name__)
        self.visited: set[str] = set()
        self.queued: set[str] = set()
        self.queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.robot_parser = RobotFileParser()

    async def crawl(self) -> CrawlResult:
        start_url = normalize_url(self.settings.start_url)
        await self._load_robots_and_sitemaps(start_url)
        await self._enqueue(start_url, 0)
        timeout = aiohttp.ClientTimeout(total=self.settings.timeout)
        connector = aiohttp.TCPConnector(limit=self.settings.concurrency, ttl_dns_cache=300, ssl=False)
        headers = {"User-Agent": self.settings.user_agent}
        async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
            workers = [asyncio.create_task(self._worker(session)) for _ in range(self.settings.concurrency)]
            await self.queue.join()
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            if self.settings.check_broken_links:
                await self._check_links(session)
        self.analyzer.analyze(self.result)
        self.result.completed_at = datetime.now(UTC)
        self._emit("Crawl complete")
        return self.result

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.set()

    def pause(self) -> None:
        self.pause_event.clear()

    def resume(self) -> None:
        self.pause_event.set()

    async def _worker(self, session: aiohttp.ClientSession) -> None:
        while not self.stop_event.is_set():
            await self.pause_event.wait()
            url, depth = await self.queue.get()
            try:
                if url not in self.visited and len(self.visited) < self.settings.max_pages:
                    await self._fetch_page(session, url, depth)
            finally:
                self.queue.task_done()

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str, depth: int) -> None:
        self.visited.add(url)
        for attempt in range(self.settings.retries + 1):
            started = perf_counter()
            try:
                async with session.get(url, allow_redirects=self.settings.follow_redirects) as response:
                    body = await response.read()
                    elapsed = perf_counter() - started
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    content_type = headers.get("content-type", "")
                    if "text/html" in content_type:
                        html = body.decode(response.charset or "utf-8", errors="replace")
                        page = self.parser.parse(str(response.url), depth, html, headers, elapsed, response.status)
                        await self._queue_page_links(page, depth)
                    else:
                        page = PageData(
                            url=str(response.url),
                            depth=depth,
                            status_code=response.status,
                            response_time=elapsed,
                            content_type=content_type,
                            page_size=len(body),
                            headers=headers,
                        )
                    self._merge_page(page)
                    self._emit(f"Crawled {url} ({response.status})")
                    return
            except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeError) as exc:
                if attempt >= self.settings.retries:
                    self.logger.warning("Failed to crawl %s: %s", url, exc)
                    self.result.pages[url] = PageData(url=url, depth=depth, status_code=0, error=str(exc))
                    self._emit(f"Failed {url}: {exc}")
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))

    async def _queue_page_links(self, page: PageData, depth: int) -> None:
        if depth >= self.settings.max_depth:
            return
        for link in page.links:
            if link.is_internal and is_html_like(link.target_url):
                await self._enqueue(link.target_url, depth + 1)

    async def _enqueue(self, url: str, depth: int) -> None:
        if url in self.queued or len(self.queued) >= self.settings.max_pages:
            return
        if not same_domain(url, self.settings.start_url):
            return
        if self.settings.respect_robots and not self.robot_parser.can_fetch(self.settings.user_agent, url):
            self._emit(f"Blocked by robots.txt: {url}")
            return
        self.queued.add(url)
        await self.queue.put((url, depth))

    async def _check_links(self, session: aiohttp.ClientSession) -> None:
        semaphore = asyncio.Semaphore(self.settings.concurrency)

        async def check(link) -> None:  # type: ignore[no-untyped-def]
            async with semaphore:
                try:
                    async with session.head(link.target_url, allow_redirects=True) as response:
                        link.status_code = response.status
                        link.redirect_chain = [str(item.url) for item in response.history]
                except aiohttp.ClientError as exc:
                    link.status_code = 0
                    link.error = str(exc)

        await asyncio.gather(*(check(link) for link in self.result.links), return_exceptions=True)

    async def _load_robots_and_sitemaps(self, start_url: str) -> None:
        root = urljoin(start_url, "/")
        robots_url = urljoin(root, "robots.txt")
        self.result.robots_txt = robots_url
        self.robot_parser.set_url(robots_url)
        self.robot_parser.parse([])
        self.result.sitemap_urls.update({urljoin(root, "sitemap.xml"), urljoin(root, "sitemap_index.xml")})

    def _merge_page(self, page: PageData) -> None:
        self.result.pages[page.url] = page
        self.result.links.extend(page.links)
        self.result.images.extend(page.images)
        self.result.resources.extend(page.resources)
        self.result.emails.update(page.emails)
        for platform, urls in page.social_profiles.items():
            self.result.social_profiles.setdefault(platform, set()).update(urls)

    def _emit(self, message: str) -> None:
        self.logger.info(message)
        if self.progress_callback:
            self.progress_callback(self.result, message)
