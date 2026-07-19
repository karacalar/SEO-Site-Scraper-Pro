"""SEO, security, and scoring analyzers."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

from seo_site_scraper_pro.models.entities import CrawlResult, PageData, SEOIssue, Severity


class SEOAnalyzer:
    """Generate actionable issues and SEO score from crawl data."""

    def analyze(self, result: CrawlResult) -> None:
        """Populate result issues and score."""

        issues: list[SEOIssue] = []
        title_counts = Counter(page.title for page in result.pages.values() if page.title)
        desc_counts = Counter(page.meta_description for page in result.pages.values() if page.meta_description)
        canonical_counts = Counter(page.canonical for page in result.pages.values() if page.canonical)
        for page in result.pages.values():
            issues.extend(self._page_issues(page, title_counts, desc_counts, canonical_counts))
            issues.extend(self._security_issues(page))
        for link in result.links:
            if link.status_code and link.status_code >= 400:
                issues.append(SEOIssue(Severity.HIGH, f"Broken {'internal' if link.is_internal else 'external'} link: {link.target_url}", "Update, remove, or redirect the broken destination.", link.source_url, "Links"))
            if len(link.redirect_chain) > 1:
                issues.append(SEOIssue(Severity.MEDIUM, f"Redirect chain detected for {link.target_url}", "Link directly to the final destination URL.", link.source_url, "Links"))
        for image in result.images:
            if image.missing_alt:
                issues.append(SEOIssue(Severity.MEDIUM, f"Image missing ALT text: {image.image_url}", "Add descriptive alternative text for accessibility and image SEO.", image.source_url, "Images"))
            if image.large_image_warning:
                issues.append(SEOIssue(Severity.LOW, f"Large image: {image.image_url}", "Compress or resize large images.", image.source_url, "Images"))
        result.issues = issues
        result.seo_score = self._score(issues)

    def _page_issues(self, page: PageData, titles: Counter[str], descriptions: Counter[str], canonicals: Counter[str]) -> list[SEOIssue]:
        issues: list[SEOIssue] = []
        checks = [
            (not page.title, Severity.HIGH, "Missing title", "Add a unique, descriptive title tag."),
            (0 < page.title_length < 30, Severity.MEDIUM, "Short title", "Expand the title to roughly 30-60 characters."),
            (page.title_length > 60, Severity.MEDIUM, "Long title", "Shorten the title to avoid truncation."),
            (bool(page.title and titles[page.title] > 1), Severity.HIGH, "Duplicate title", "Write a unique title for each indexable page."),
            (not page.meta_description, Severity.HIGH, "Missing meta description", "Add a compelling meta description."),
            (0 < page.description_length < 70, Severity.LOW, "Short description", "Expand the description to summarize the page."),
            (page.description_length > 160, Severity.LOW, "Long description", "Shorten the description to avoid truncation."),
            (bool(page.meta_description and descriptions[page.meta_description] > 1), Severity.MEDIUM, "Duplicate description", "Write a unique description for each page."),
            (len(page.h1) > 1, Severity.MEDIUM, "Multiple H1", "Use one primary H1 heading."),
            (not page.h1, Severity.HIGH, "Missing H1", "Add one clear H1 heading."),
            (not page.canonical, Severity.MEDIUM, "Missing canonical", "Add a canonical link element."),
            ("noindex" in page.meta_robots.lower(), Severity.INFO, "Noindex page", "Verify this page should be excluded from search."),
            ("nofollow" in page.meta_robots.lower(), Severity.INFO, "Nofollow page", "Verify links on this page should not pass signals."),
            (page.word_count < 300, Severity.MEDIUM, "Thin content", "Add helpful, original content."),
            (page.page_size > 1_000_000, Severity.LOW, "Large page", "Reduce HTML payload size."),
            (not page.open_graph, Severity.LOW, "Missing Open Graph", "Add Open Graph metadata."),
            (not page.twitter_cards, Severity.LOW, "Missing Twitter Cards", "Add Twitter/X card metadata."),
            (not page.structured_data, Severity.LOW, "Missing Schema.org", "Add JSON-LD structured data where relevant."),
            (bool(page.canonical and canonicals[page.canonical] > 1), Severity.MEDIUM, "Duplicate canonical", "Ensure canonical URLs point to the correct preferred page."),
        ]
        return [SEOIssue(severity, description, recommendation, page.url, "SEO") for condition, severity, description, recommendation in checks if condition]

    def _security_issues(self, page: PageData) -> list[SEOIssue]:
        headers = {key.lower(): value for key, value in page.headers.items()}
        issues = []
        if urlparse(page.url).scheme != "https":
            issues.append(SEOIssue(Severity.HIGH, "Page is not served over HTTPS", "Enable HTTPS across the site.", page.url, "Security"))
        for header, label in {"strict-transport-security": "HSTS", "content-security-policy": "Content Security Policy", "x-frame-options": "X-Frame-Options", "referrer-policy": "Referrer Policy", "permissions-policy": "Permissions Policy"}.items():
            if header not in headers:
                issues.append(SEOIssue(Severity.LOW, f"Missing {label}", f"Configure the {label} response header.", page.url, "Security"))
        if "server" in headers:
            issues.append(SEOIssue(Severity.INFO, "Server header exposed", "Consider minimizing server version disclosure.", page.url, "Security"))
        if "x-powered-by" in headers:
            issues.append(SEOIssue(Severity.INFO, "Powered By header exposed", "Remove technology disclosure headers when possible.", page.url, "Security"))
        return issues

    def _score(self, issues: list[SEOIssue]) -> int:
        weights = {Severity.CRITICAL: 10, Severity.HIGH: 6, Severity.MEDIUM: 3, Severity.LOW: 1, Severity.INFO: 0}
        return max(0, 100 - sum(weights[issue.severity] for issue in issues))
