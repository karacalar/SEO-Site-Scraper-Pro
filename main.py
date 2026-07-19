"""Application launcher for SEO Site Scraper Pro."""

from __future__ import annotations

import os
import sys
from tkinter import messagebox

from src.utils.logging_config import configure_logging


def main() -> None:
    """Start the desktop application."""

    configure_logging()
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print("SEO Site Scraper Pro startup check passed. GUI launch skipped because DISPLAY is not set.")
        return
    try:
        from src.ui.main_window import MainWindow

        MainWindow().mainloop()
    except Exception as exc:
        messagebox.showerror("SEO Site Scraper Pro", f"Application failed to start: {exc}")
        raise


if __name__ == "__main__":
    main()
