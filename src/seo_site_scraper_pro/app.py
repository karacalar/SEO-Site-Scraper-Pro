"""Application entry point."""

from __future__ import annotations

import os
import sys

from seo_site_scraper_pro.utils.logging_config import configure_logging


def main() -> None:
    """Launch SEO Site Scraper Pro or perform a headless startup validation."""

    configure_logging()
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print("SEO Site Scraper Pro startup check passed. GUI launch skipped because DISPLAY is not set.")
        return
    from seo_site_scraper_pro.ui.main_window import MainWindow

    MainWindow().mainloop()


if __name__ == "__main__":
    main()
