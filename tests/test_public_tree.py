from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".json", ".md", ".py", ".toml", ".yml", ".yaml"}
FORBIDDEN = {
    "absolute macOS user path": re.compile(r"/" r"Users/"),
    "absolute Linux user path": re.compile(r"/" r"home/"),
    "concrete USB modem identifier": re.compile(r"usbmodem[0-9A-Fa-f]{8,}"),
}


def tracked_text_files() -> list[Path]:
    names = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return [ROOT / name for name in names if Path(name).suffix in TEXT_SUFFIXES]


def test_public_tree_has_no_personal_paths_or_usb_serials():
    failures = []
    for path in tracked_text_files():
        text = path.read_text(errors="ignore")
        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: {label}")
    assert failures == []
