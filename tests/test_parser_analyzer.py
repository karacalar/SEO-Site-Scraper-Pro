from src.analyzer.analyzer import SEOAnalyzer
from src.models.entities import CrawlResult, CrawlSettings
from src.parser.page_parser import PageParser


def test_parser_extracts_core_seo_entities() -> None:
    html = """
    <html lang='en'><head><title>Example Title</title>
    <meta name='description' content='A useful page description for testing.'>
    <link rel='canonical' href='/canonical'><meta property='og:title' content='OG'>
    <meta name='twitter:card' content='summary'><script type='application/ld+json'>{}</script>
    </head><body><h1>Main</h1><h2>Sub</h2><a href='/about' rel='nofollow sponsored'>About</a>
    <a href='https://github.com/example'>GitHub</a><img src='/logo.png' loading='lazy'>
    <p>Contact hello@example.com with enough visible words for parsing.</p></body></html>
    """
    page = PageParser().parse("https://example.com/", 0, html, {"content-type": "text/html"}, 0.25, 200)
    assert page.title == "Example Title"
    assert page.canonical == "https://example.com/canonical"
    assert page.internal_links_count == 1
    assert page.external_links_count == 1
    assert page.images[0].missing_alt is True
    assert "hello@example.com" in page.emails
    assert "GitHub" in page.social_profiles


def test_analyzer_scores_missing_metadata() -> None:
    html = "<html><body><p>Thin page</p><img src='/a.png'></body></html>"
    page = PageParser().parse("http://example.com/", 0, html, {"server": "nginx"}, 0.1, 200)
    result = CrawlResult(CrawlSettings("http://example.com/"), pages={page.url: page}, images=page.images)
    SEOAnalyzer().analyze(result)
    descriptions = {issue.description for issue in result.issues}
    assert "Missing title" in descriptions
    assert "Missing meta description" in descriptions
    assert "HTTP page" in descriptions
    assert result.seo_score < 100
