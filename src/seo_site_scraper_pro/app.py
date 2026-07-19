"""Application entry point."""

from __future__ import annotations

from seo_site_scraper_pro.ui.main_window import MainWindow
from seo_site_scraper_pro.utils.logging_config import configure_logging


def main() -> None:
    """Launch SEO Site Scraper Pro."""

    configure_logging()
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
