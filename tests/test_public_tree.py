import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_FILE = Path(__file__).resolve()
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml"}
BANNED = {
    "personal absolute path": re.compile(r"/Users/[^/\s]+/"),
    "hardware-specific USB serial": re.compile(
        r"/dev/tty\.usbmodem[0-9A-Za-z]{6,}"
    ),
}


def eligible_text_files() -> list[Path]:
    names = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    return [
        ROOT / name
        for name in names
        if name and Path(name).suffix.lower() in TEXT_SUFFIXES
    ]


def public_text_files() -> list[Path]:
    return [path for path in eligible_text_files() if path != CONTROL_FILE]


def test_control_file_is_the_only_eligible_file_excluded() -> None:
    eligible = set(eligible_text_files())
    scanned = set(public_text_files())
    assert eligible - scanned == {CONTROL_FILE}


def test_git_ignored_file_is_not_public() -> None:
    ignored = ROOT / ".pytest_cache" / "public-tree-control.py"
    ignored.parent.mkdir(exist_ok=True)
    ignored.write_text("local dependency fixture", encoding="utf-8")
    try:
        assert ignored not in eligible_text_files()
    finally:
        ignored.unlink(missing_ok=True)


def test_public_tree_has_no_personal_paths_or_usb_serials() -> None:
    violations: list[str] = []
    for path in public_text_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in BANNED.items():
            if pattern.search(text):
                violations.append(f"{path.relative_to(ROOT)}: {label}")
    assert violations == []
