# SEO Site Scraper Pro

SEO Site Scraper Pro is a professional Windows desktop SEO crawler written in Python 3.12+ with CustomTkinter. It provides concurrent crawling, SEO analysis, image and link audits, email/social discovery, security checks, sitemap and robots.txt discovery, live logging, and commercial report exports.

## Run on Windows 10/11

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Project layout

```text
main.py
requirements.txt
assets/
config/
logs/
reports/
src/
  ui/
  crawler/
  parser/
  analyzer/
  exporters/
  models/
  utils/
tests/
```

## Features

- Modern dark CustomTkinter GUI with sidebar, toolbar, dashboard, status bar, progress bar, and responsive layout.
- Async `aiohttp` crawler with queue-based concurrency, max depth/pages, retry, timeout, custom user agent, pause, resume, stop, and progress updates.
- SEO analysis for titles, descriptions, H1/H2, canonicals, robots, Open Graph, Twitter Cards, Schema, image ALT, duplicate metadata, broken links, status codes, and response time.
- Email finder, social media detector, security checker, sitemap detector, robots.txt reader, and live console logging to `logs/application.log`.
- Export to Excel, CSV, JSON, and professional HTML report files under `reports/`.
