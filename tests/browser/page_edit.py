"""A self-test's edited copy of a built page, its CSP re-hashed as the build would (Stage 88 item 5).

The pages allow only their own inline scripts, named by hash. A self-test that edits a page's script to
plant a defect must re-hash the page, or the browser refuses the whole script and the check meets a dead
page instead of the defect. A real build hashes whatever script it ships (src/core/csp.py), so the re-hashed
copy is the page the defect would ship as. A page with no CSP meta (a hand-written fixture) is unchanged.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.csp import CSP_RE, harden


def rehash(html: str) -> str:
    """The page with its script-src naming the scripts it now holds."""
    return harden(html) if CSP_RE.search(html) else html
