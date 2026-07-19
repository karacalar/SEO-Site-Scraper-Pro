"""SEO and security analysis engine."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

from src.models.entities import CrawlResult, PageData, SEOIssue, Severity


class SEOAnalyzer:
    """Generate actionable SEO and security issues and a 0-100 score."""

    def analyze(self, result: CrawlResult) -> None:
        title_counts = Counter(page.title for page in result.pages.values() if page.title)
        desc_counts = Counter(page.meta_description for page in result.pages.values() if page.meta_description)
        issues: list[SEOIssue] = []
        for page in result.pages.values():
            issues.extend(self._page_issues(page, title_counts, desc_counts))
            issues.extend(self._security_issues(page))
        for link in result.links:
            if link.status_code and link.status_code >= 400:
                issues.append(
                    SEOIssue(
                        Severity.HIGH,
                        f"Broken link: {link.target_url}",
                        "Update, remove, or redirect the broken destination.",
                        link.source_url,
                        "Links",
                    )
                )
        for image in result.images:
            if image.missing_alt:
                issues.append(
                    SEOIssue(
                        Severity.MEDIUM,
                        f"Image missing ALT text: {image.image_url}",
                        "Add concise, descriptive alternative text.",
                        image.source_url,
                        "Images",
                    )
                )
        result.issues = issues
        result.seo_score = self._score(issues)

    def _page_issues(
        self,
        page: PageData,
        title_counts: Counter[str],
        desc_counts: Counter[str],
    ) -> list[SEOIssue]:
        checks = [
            (not page.title, Severity.HIGH, "Missing title", "Add a unique descriptive title tag."),
            (0 < page.title_length < 30, Severity.MEDIUM, "Short title", "Use 30-60 characters."),
            (page.title_length > 60, Severity.MEDIUM, "Long title", "Keep titles concise."),
            (bool(page.title and title_counts[page.title] > 1), Severity.HIGH, "Duplicate title", "Create a unique title."),
            (not page.meta_description, Severity.HIGH, "Missing meta description", "Add a compelling description."),
            (page.description_length > 160, Severity.LOW, "Long description", "Keep descriptions under 160 characters."),
            (bool(page.meta_description and desc_counts[page.meta_description] > 1), Severity.MEDIUM, "Duplicate description", "Create a unique description."),
            (not page.h1, Severity.HIGH, "Missing H1", "Add one clear H1 heading."),
            (len(page.h1) > 1, Severity.MEDIUM, "Multiple H1", "Use one primary H1 heading."),
            (not page.canonical, Severity.MEDIUM, "Missing canonical", "Add a canonical link element."),
            ("noindex" in page.meta_robots.lower(), Severity.INFO, "Noindex page", "Confirm this page should be excluded."),
            (page.word_count < 300, Severity.MEDIUM, "Thin content", "Add helpful original content."),
            (not page.open_graph, Severity.LOW, "Missing Open Graph", "Add Open Graph metadata."),
            (not page.twitter_cards, Severity.LOW, "Missing Twitter Cards", "Add Twitter/X card metadata."),
            (not page.structured_data, Severity.LOW, "Missing Schema", "Add JSON-LD structured data where useful."),
        ]
        return [
            SEOIssue(severity, description, recommendation, page.url, "SEO")
            for condition, severity, description, recommendation in checks
            if condition
        ]

    def _security_issues(self, page: PageData) -> list[SEOIssue]:
        headers = {key.lower(): value for key, value in page.headers.items()}
        issues: list[SEOIssue] = []
        if urlparse(page.url).scheme != "https":
            issues.append(SEOIssue(Severity.HIGH, "HTTP page", "Serve every page over HTTPS.", page.url, "Security"))
        required_headers = {
            "strict-transport-security": "HSTS",
            "content-security-policy": "Content Security Policy",
            "x-frame-options": "X-Frame-Options",
            "referrer-policy": "Referrer Policy",
            "permissions-policy": "Permissions Policy",
        }
        for header, label in required_headers.items():
            if header not in headers:
                issues.append(SEOIssue(Severity.LOW, f"Missing {label}", f"Configure {label}.", page.url, "Security"))
        if "server" in headers:
            issues.append(SEOIssue(Severity.INFO, "Server header exposed", "Minimize server disclosure.", page.url, "Security"))
        return issues

    def _score(self, issues: list[SEOIssue]) -> int:
        weights = {Severity.CRITICAL: 10, Severity.HIGH: 6, Severity.MEDIUM: 3, Severity.LOW: 1, Severity.INFO: 0}
        return max(0, 100 - sum(weights[issue.severity] for issue in issues))
