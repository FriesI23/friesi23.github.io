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

import argparse
import re
import sys
from pathlib import Path

STUB = "---\n---\n"


def _prompt_file(md_path: Path) -> str | None:
    text = md_path.read_text(encoding="utf-8")
    fm = re.search(r"^---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not fm:
        return None
    m = re.search(r"^prompt_file:\s*(\S+)\s*$", fm.group(1), re.MULTILINE)
    return m.group(1).strip() if m else None


def main(root: Path) -> int:
    prompts_dir = root / "_prompts"
    includes_dir = root / "_includes"
    assets_dir = root / "assets"

    if not prompts_dir.exists():
        print(f"[sync-prompts] {prompts_dir} not found", file=sys.stderr)
        return 1

    referenced: set[str] = set()
    for md_path in sorted(prompts_dir.glob("*.md")):
        prompt_file = _prompt_file(md_path)
        if not prompt_file:
            print(f"[sync-prompts] WARN: {md_path.relative_to(root)} has no prompt_file", file=sys.stderr)
            continue
        referenced.add(prompt_file)

        include_path = includes_dir / prompt_file
        include_path = include_path.with_suffix(".md")
        if not include_path.exists():
            print(f"[sync-prompts] WARN: missing {include_path.relative_to(root)} for {md_path.name}", file=sys.stderr)

        asset_path = assets_dir / prompt_file
        if not asset_path.exists():
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_text(STUB, encoding="utf-8")
            print(f"[sync-prompts] created {asset_path.relative_to(root)}")

    prompts_assets_dir = assets_dir / "prompts"
    if prompts_assets_dir.exists():
        for asset_path in sorted(prompts_assets_dir.glob("*.txt")):
            rel = asset_path.relative_to(assets_dir).as_posix()
            if rel not in referenced:
                asset_path.unlink()
                print(f"[sync-prompts] removed orphaned {asset_path.relative_to(root)}")

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Sync assets/prompts stubs with _prompts collection.")
    p.add_argument(
        "--root",
        type=Path,
        required=True,
        metavar="DIR",
        help="Repo root directory",
    )
    args = p.parse_args()
    raise SystemExit(main(args.root.resolve()))
