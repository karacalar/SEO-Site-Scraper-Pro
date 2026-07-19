from pathlib import Path


def test_required_project_files_exist() -> None:
    required = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        "main.py",
        "src/ui/main_window.py",
        "src/crawler/crawler.py",
        "src/parser/page_parser.py",
        "src/analyzer/analyzer.py",
        "src/exporters/exporter.py",
        "src/models/entities.py",
        "src/utils/logging_config.py",
        "src/utils/url_tools.py",
        "assets",
        "config",
        "logs/.gitkeep",
        "reports/.gitkeep",
    ]
    for file_name in required:
        assert Path(file_name).exists(), file_name


def test_no_packaging_layout_or_pyproject() -> None:
    assert not Path("pyproject.toml").exists()
    assert not Path("src/seo_site_scraper_pro").exists()


def test_requirements_contains_every_dependency() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    for package in ["aiohttp", "beautifulsoup4", "lxml", "customtkinter", "requests", "pandas", "openpyxl", "validators", "tldextract", "Pillow", "networkx", "matplotlib"]:
        assert package in requirements
