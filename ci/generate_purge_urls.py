"""Generate a purge-URL list from changed _posts/ files.

Writes one absolute URL per line to output_file (or stdout).
Falls back to ci/purge_urls.txt when before_sha is all-zeros
(initial / force push), no _posts/ changes are detected, or the
number of changed posts exceeds BULK_THRESHOLD.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SITE_URL = "https://friesi23.icu"
BULK_THRESHOLD = 10

# Mirrors permalink / archive rules in _config.yml
_POST_URL = "/post/{year}{month}/{slug}"
_MONTH_URL = "/post/{year}{month}/"
_CATEGORY_URL = "/categories/{category}/"
_TAG_URL = "/tags/{tag}/"

# Always purge these regardless of which posts changed:
# homepage listing, pagination, global archives and sitemap.
FIXED_URLS = ["/", "/page1/", "/categories/", "/tags/", "/sitemap.xml"]


def _post_parts(filepath: str) -> dict | None:
    """Derive year, month, slug from a post filepath like _posts/ai/2024-01-15-my-slug.md."""
    stem = Path(filepath).stem
    m = re.match(r"^(\d{4})-(\d{2})-\d{2}-(.+)$", stem)
    if not m:
        return None
    return {"year": m.group(1), "month": m.group(2), "slug": m.group(3)}


def _parse_fm(content: str) -> dict:
    """Extract category and tags from YAML front matter using regex only."""
    info: dict = {"category": None, "tags": []}
    fm = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm:
        return info
    body = fm.group(1)

    m = re.search(r"^category:\s*(\S+)", body, re.MULTILINE)
    if m:
        info["category"] = m.group(1).strip().lower()

    # Inline list: tags: [tag1, tag2]
    m = re.search(r"^tags:\s*\[([^\]]*)\]", body, re.MULTILINE)
    if m:
        info["tags"] = [
            t.strip().strip("\"'").lower()
            for t in m.group(1).split(",")
            if t.strip()
        ]
    else:
        # Single-value fallback: tags: my-tag
        m = re.search(r"^tags:\s*(\S+)", body, re.MULTILINE)
        if m:
            info["tags"] = [m.group(1).lower()]

    return info


def _git_show(sha: str, path: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return r.stdout
    except subprocess.CalledProcessError:
        return None


def _urls_for(filepath: str, content: str | None) -> list[str]:
    parts = _post_parts(filepath)
    if not parts:
        return []
    urls = [_POST_URL.format(**parts), _MONTH_URL.format(**parts)]
    if content:
        fm = _parse_fm(content)
        if fm["category"]:
            urls.append(_CATEGORY_URL.format(category=fm["category"]))
        for tag in fm["tags"]:
            slug = re.sub(r"[^a-z0-9]+", "-", tag).strip("-")
            if slug:
                urls.append(_TAG_URL.format(tag=slug))
    return urls


def _changed_posts(before: str, current: str) -> list[tuple[str, str, str]]:
    r = subprocess.run(
        ["git", "diff", "--name-status", before, current],
        capture_output=True,
        text=True,
        check=True,
    )
    out = []
    for line in r.stdout.splitlines():
        cols = line.split("\t")
        status = cols[0]
        if status.startswith("R") and len(cols) == 3:
            old, new = cols[1], cols[2]
            if "_posts/" in old or "_posts/" in new:
                out.append(("R", old, new))
        elif status in ("A", "M", "D") and len(cols) == 2:
            path = cols[1]
            if "_posts/" in path:
                out.append((status, path, path))
    return out


def generate(before: str, current: str) -> list[str] | None:
    """Return sorted path list, or None to signal use of static fallback."""
    if re.fullmatch(r"0+", before):
        print("[purge] Initial / force push detected; using static fallback.", file=sys.stderr)
        return None

    changed = _changed_posts(before, current)
    if not changed:
        print("[purge] No _posts/ changes detected; using static fallback.", file=sys.stderr)
        return None

    if len(changed) > BULK_THRESHOLD:
        print(
            f"[purge] {len(changed)} posts changed (>{BULK_THRESHOLD}); "
            "using static fallback.",
            file=sys.stderr,
        )
        return None

    paths: set[str] = set()
    for status, old, new in changed:
        if status == "D":
            for u in _urls_for(old, _git_show(before, old)):
                paths.add(u)
        elif status in ("A", "M"):
            for u in _urls_for(new, _git_show(current, new)):
                paths.add(u)
        else:  # R (rename)
            for u in _urls_for(old, _git_show(before, old)):
                paths.add(u)
            for u in _urls_for(new, _git_show(current, new)):
                paths.add(u)

    for p in FIXED_URLS:
        paths.add(p)

    return sorted(paths)


def _load_static(filepath: Path, site_url: str) -> list[str]:
    if not filepath.exists():
        return []
    urls = []
    for line in filepath.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line if line.startswith("http") else site_url + line)
    return urls


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Generate a purge-URL list from changed _posts/ files. "
            "Falls back to purge_urls.txt on initial push, no post changes, "
            "or bulk edits exceeding BULK_THRESHOLD."
        )
    )
    p.add_argument("before_sha", help="SHA of the commit before the push")
    p.add_argument("current_sha", help="SHA of the current (head) commit")
    p.add_argument(
        "--site-url",
        default=SITE_URL,
        help=f"Absolute site base URL, no trailing slash (default: {SITE_URL})",
    )
    p.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write URLs to FILE instead of stdout",
    )
    p.add_argument(
        "--static-list",
        metavar="FILE",
        default=None,
        help="Fallback URL list (default: purge_urls.txt next to this script)",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()

    before_sha = args.before_sha or "0" * 40
    static_path = (
        Path(args.static_list)
        if args.static_list
        else Path(__file__).parent / "purge_urls.txt"
    )

    paths = generate(before_sha, args.current_sha)
    if paths is None:
        absolute_urls = _load_static(static_path, args.site_url)
    else:
        absolute_urls = [args.site_url + p for p in paths]

    print(f"[purge] {len(absolute_urls)} URL(s) queued:", file=sys.stderr)
    for u in absolute_urls:
        print(f"  {u}", file=sys.stderr)

    text = "\n".join(absolute_urls) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text, end="")
