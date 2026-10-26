"""Where the build finds things.

The scripts run in two layouts: in the repository, as eu27/ beside europe/ and uk/, and in a
working copy that sits beside the repository folder. DELIV is the repository root in both, found
by looking for europe/tool_machinery one level up.
"""
import contextlib
import os
import shutil
import tempfile

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(BUILD, ".."))
_UP = os.path.normpath(os.path.join(ROOT, ".."))
DELIV = _UP if os.path.isdir(os.path.join(_UP, "europe", "tool_machinery")) else os.path.join(_UP, "Deliverable")
MACH = os.path.join(DELIV, "europe", "tool_machinery")
# The plain-language view's source page (the provider-only tool of September 2026).
LITE_SOURCE = os.path.join(BUILD, "plain_language_source.html")


@contextlib.contextmanager
def short_workdir():
    """A scratch folder for Chrome's profile and the probe pages, in the system temp folder and
    removed afterwards. Not beside the scripts: Windows refuses a Chrome profile path longer than
    its path limit, and a checkout in a deep folder reaches it (Chrome then stops on a dialog
    instead of exiting, and the check hangs)."""
    d = tempfile.mkdtemp(prefix="eu27chk_")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def file_url(p):
    return "file:///" + p.replace("\\", "/").replace(" ", "%20")


def chrome():
    """Chrome or Chromium. CHROME_BINARY overrides."""
    cands = [os.environ.get("CHROME_BINARY")]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            cands.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    cands.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    for c in cands:
        if c and os.path.isfile(c):
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    raise SystemExit("Chrome not found: set CHROME_BINARY to its path")
