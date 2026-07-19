# SEO Site Scraper Pro

SEO Site Scraper Pro is a premium-feeling desktop SEO crawler written entirely in Python. It uses a modern CustomTkinter interface and an asynchronous aiohttp crawler to collect page, link, image, resource, security, sitemap, email, social, and SEO issue data.

## Features

- Dark themed desktop UI with dashboard, analysis tabs, settings, live logging, pause/resume/stop controls, filters, and global search.
- Async queue-based crawler with connection pooling, depth limits, concurrency, timeouts, redirect support, and UI-safe worker thread integration.
- Page analysis for titles, meta descriptions, headings, canonicals, robots directives, language, charset, structured data, Open Graph, Twitter Cards, status, size, response time, headers, and content metrics.
- SEO issue detection with severity, recommendations, affected URLs, score, top issues, and priority fixes.
- Link, image, resource, email, social media, security, robots.txt, and sitemap discovery.
- Export support for CSV, JSON, Excel, and professional HTML reports.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
seo-site-scraper-pro
```

## Tests

```bash
pytest
```
