"""Report exporters for SEO Site Scraper Pro."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from seo_site_scraper_pro.models.entities import CrawlResult


class ReportExporter:
    """Export crawl results to CSV, JSON, Excel, and HTML."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: CrawlResult, stem: str = "seo_report") -> dict[str, Path]:
        """Export all supported report formats."""

        return {
            "csv": self.to_csv(result, f"{stem}_pages.csv"),
            "json": self.to_json(result, f"{stem}.json"),
            "xlsx": self.to_xlsx(result, f"{stem}.xlsx"),
            "html": self.to_html(result, f"{stem}.html"),
        }

    def to_csv(self, result: CrawlResult, filename: str) -> Path:
        path = self.output_dir / filename
        rows = [self._page_row(page) for page in result.pages.values()]
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else ["url"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def to_json(self, result: CrawlResult, filename: str) -> Path:
        path = self.output_dir / filename
        path.write_text(json.dumps(self._safe(result), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def to_xlsx(self, result: CrawlResult, filename: str) -> Path:
        path = self.output_dir / filename
        workbook = Workbook()
        pages = workbook.active
        pages.title = "Pages"
        rows = [self._page_row(page) for page in result.pages.values()]
        if rows:
            pages.append(list(rows[0].keys()))
            for row in rows:
                pages.append(list(row.values()))
        issues = workbook.create_sheet("Issues")
        issues.append(["Severity", "Category", "URL", "Description", "Recommendation"])
        for issue in result.issues:
            issues.append([issue.severity.value, issue.category, issue.affected_url, issue.description, issue.recommendation])
        workbook.save(path)
        return path

    def to_html(self, result: CrawlResult, filename: str) -> Path:
        path = self.output_dir / filename
        summary = result.as_summary()
        issue_rows = "".join(f"<tr><td>{i.severity.value}</td><td>{i.category}</td><td>{i.affected_url}</td><td>{i.description}</td><td>{i.recommendation}</td></tr>" for i in result.issues)
        page_rows = "".join(f"<tr><td>{p.url}</td><td>{p.status_code}</td><td>{p.title}</td><td>{p.word_count}</td><td>{p.response_time:.2f}s</td></tr>" for p in result.pages.values())
        html = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><title>SEO Site Scraper Pro Report</title><style>body{{font-family:Inter,Arial;background:#111827;color:#f9fafb;margin:32px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}}.card{{background:#1f2937;border:1px solid #374151;border-radius:14px;padding:18px}}table{{width:100%;border-collapse:collapse;margin-top:24px;background:#1f2937}}th,td{{border-bottom:1px solid #374151;padding:10px;text-align:left}}th{{color:#93c5fd}}.score{{font-size:42px;color:#22c55e}}</style></head><body><h1>SEO Site Scraper Pro Report</h1><p class='score'>SEO Score: {result.seo_score}/100</p><section class='cards'>{''.join(f"<div class='card'><strong>{k.replace('_',' ').title()}</strong><br>{v}</div>" for k, v in summary.items())}</section><h2>Issues</h2><table><tr><th>Severity</th><th>Category</th><th>URL</th><th>Issue</th><th>Recommendation</th></tr>{issue_rows}</table><h2>Pages</h2><table><tr><th>URL</th><th>Status</th><th>Title</th><th>Words</th><th>Response</th></tr>{page_rows}</table></body></html>"""
        path.write_text(html, encoding="utf-8")
        return path

    def _page_row(self, page: Any) -> dict[str, Any]:
        return {"url": page.url, "status_code": page.status_code, "depth": page.depth, "title": page.title, "title_length": page.title_length, "meta_description": page.meta_description, "description_length": page.description_length, "h1": " | ".join(page.h1), "h2_count": page.h2_count, "h3_count": page.h3_count, "canonical": page.canonical, "word_count": page.word_count, "internal_links": page.internal_links_count, "external_links": page.external_links_count, "images": page.image_count, "response_time": page.response_time}

    def _safe(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._safe(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._safe(item) for item in value]
        if hasattr(value, "value"):
            return value.value
        if isinstance(value, Path):
            return str(value)
        return value
