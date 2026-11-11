"""The README's tables come from the committed result files."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_tables_are_current():
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts/make_readme_tables.py"), "--check"],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_readme_says_no_answer_is_confirmed_or_verified():
    text = (ROOT / "README.md").read_text().lower()
    for word in ("confirmed", "verified"):
        assert word not in text
