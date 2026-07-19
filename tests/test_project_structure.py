from pathlib import Path
import tomllib


def test_required_project_files_exist() -> None:
    required = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        "pyproject.toml",
        "main.py",
        "src/seo_site_scraper_pro/app.py",
        "src/seo_site_scraper_pro/ui/__init__.py",
        "src/seo_site_scraper_pro/crawler/__init__.py",
        "src/seo_site_scraper_pro/analyzer/__init__.py",
        "src/seo_site_scraper_pro/parser/__init__.py",
        "src/seo_site_scraper_pro/models/__init__.py",
        "src/seo_site_scraper_pro/exporters/__init__.py",
        "src/seo_site_scraper_pro/utils/__init__.py",
        "assets/__init__.py",
        "config/__init__.py",
        "logs/.gitkeep",
        "reports/.gitkeep",
    ]
    for file_name in required:
        assert Path(file_name).exists(), file_name


def test_pyproject_declares_entrypoint_and_dependencies() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["requires-python"] == ">=3.13"
    assert project["project"]["scripts"]["seo-site-scraper-pro"] == "seo_site_scraper_pro.app:main"
    dependencies = set(project["project"]["dependencies"])
    for package in ["aiohttp", "beautifulsoup4", "lxml", "customtkinter", "pandas", "openpyxl", "tldextract", "validators", "Pillow", "networkx", "matplotlib", "requests"]:
        assert any(dependency.startswith(package) for dependency in dependencies)
