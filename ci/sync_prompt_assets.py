"""Sync assets/prompts/<name>.txt stub files with the _prompts/*.md collection.

For each _prompts/<name>.md with a `prompt_file: prompts/<name>.txt` front
matter field, ensures assets/<prompt_file> exists as an empty front matter
stub (`---\\n---\\n`) so prompt-raw.html can serve it via include. The actual
prompt content lives in _includes/<prompt_file> with a `.md` extension
instead (e.g. _includes/prompts/<name>.md); both layouts derive this by
swapping the `.txt` suffix for `.md`. Also removes stub files under
assets/prompts/ that no longer correspond to any _prompts/*.md entry.

Run locally after adding/removing/renaming prompt collection entries, then
commit the result.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "_prompts"
INCLUDES_DIR = ROOT / "_includes"
ASSETS_DIR = ROOT / "assets"
STUB = "---\n---\n"


def _prompt_file(md_path: Path) -> str | None:
    text = md_path.read_text(encoding="utf-8")
    fm = re.search(r"^---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not fm:
        return None
    m = re.search(r"^prompt_file:\s*(\S+)\s*$", fm.group(1), re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> int:
    if not PROMPTS_DIR.exists():
        print(f"[sync-prompts] {PROMPTS_DIR} not found", file=sys.stderr)
        return 1

    referenced: set[str] = set()
    for md_path in sorted(PROMPTS_DIR.glob("*.md")):
        prompt_file = _prompt_file(md_path)
        if not prompt_file:
            print(f"[sync-prompts] WARN: {md_path.relative_to(ROOT)} has no prompt_file", file=sys.stderr)
            continue
        referenced.add(prompt_file)

        include_path = INCLUDES_DIR / prompt_file
        include_path = include_path.with_suffix(".md")
        if not include_path.exists():
            print(f"[sync-prompts] WARN: missing {include_path.relative_to(ROOT)} for {md_path.name}", file=sys.stderr)

        asset_path = ASSETS_DIR / prompt_file
        if not asset_path.exists():
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_text(STUB, encoding="utf-8")
            print(f"[sync-prompts] created {asset_path.relative_to(ROOT)}")

    prompts_assets_dir = ASSETS_DIR / "prompts"
    if prompts_assets_dir.exists():
        for asset_path in sorted(prompts_assets_dir.glob("*.txt")):
            rel = asset_path.relative_to(ASSETS_DIR).as_posix()
            if rel not in referenced:
                asset_path.unlink()
                print(f"[sync-prompts] removed orphaned {asset_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
