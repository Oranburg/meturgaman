"""Print an HTML page to a PDF with a headless Chromium browser, on any platform.

A reading pack is hand-edited HTML, and the HTML is its source: it travels
beside the PDF so the pack can be revised. This module is the printer, so the
same command works on the Windows PC and the Mac.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

__all__ = ["find_browser", "print_pdf", "pages"]

_CANDIDATES = {
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
}
_ON_PATH = ["google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]


def find_browser(explicit: str | None = None) -> str:
    if explicit:
        if Path(explicit).exists():
            return explicit
        raise OSError(f"no browser at {explicit}")
    for candidate in _CANDIDATES.get(platform.system(), []):
        if Path(candidate).exists():
            return candidate
    for name in _ON_PATH:
        found = shutil.which(name)
        if found:
            return found
    raise OSError("no Chrome, Edge or Chromium found; pass --browser with its path")


def pages(pdf: Path) -> int:
    """Count pages by reading the PDF's own page objects."""
    import re
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def print_pdf(html: str | Path, pdf: str | Path, *, browser: str | None = None,
              timeout: float = 120.0) -> Path:
    html, pdf = Path(html).resolve(), Path(pdf).resolve()
    if not html.exists():
        raise OSError(f"no such page: {html}")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    # A profile of its own: a headless print against a running browser's
    # profile fails on Windows with "Access is denied" and writes nothing.
    with tempfile.TemporaryDirectory(prefix="meturgaman-print-") as profile:
        command = [find_browser(browser), "--headless", "--disable-gpu",
                   "--no-sandbox", f"--user-data-dir={profile}",
                   "--no-pdf-header-footer", f"--print-to-pdf={pdf}", html.as_uri()]
        done = subprocess.run(command, capture_output=True, text=True,
                              timeout=timeout, env=dict(os.environ))
    if not pdf.exists() or pdf.stat().st_size == 0:
        raise OSError(f"the browser wrote no PDF: {(done.stderr or done.stdout)[-300:]}")
    return pdf
