"""Shared helpers for resolving which post/prompt URLs changed in a push.

Used by the Google/Baidu/Bing submission scripts so each only notifies search
engines about posts and prompts added or modified between before_sha and
after_sha, instead of resubmitting the whole sitemap on every push.
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import lxml.etree

# Mirrors permalink rules in _config.yml
_POST_PATH = re.compile(r"^/post/\d{6}/[^/]+/?$")
_PROMPT_PATH = re.compile(r"^/prompts/[^/]+$")  # excludes the bare /prompts/ index


def sitemap_urls(sitemap_path: str) -> list[str]:
    tree = lxml.etree.parse(sitemap_path)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return tree.xpath("//s:url/s:loc/text()", namespaces=ns)


def filter_post_prompt_urls(urls: list[str]) -> list[str]:
    return [u for u in urls if _POST_PATH.match(urlparse(u).path) or _PROMPT_PATH.match(urlparse(u).path)]


def changed_files(before_sha: str, after_sha: str) -> list[str]:
    if re.fullmatch(r"0+", before_sha):
        return []
    # No pathspec here: git resolves pathspecs relative to cwd, which may not
    # be the repo root (e.g. when invoked via `poetry -C ci run`). Diff
    # everything and filter the root-relative output paths in Python instead.
    r = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", before_sha, after_sha],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def post_url(filepath: str, site_url: str) -> str | None:
    stem = Path(filepath).stem
    m = re.match(r"^(\d{4})-(\d{2})-\d{2}-(.+)$", stem)
    if not m:
        return None
    year, month, slug = m.groups()
    return f"{site_url}/post/{year}{month}/{slug}"


def prompt_url(filepath: str, site_url: str) -> str:
    rel = Path(filepath).relative_to("_prompts").with_suffix("")
    return f"{site_url}/prompts/{rel}"


def changed_urls(before_sha: str, after_sha: str, site_url: str) -> set[str]:
    urls: set[str] = set()
    for f in changed_files(before_sha, after_sha):
        if f.startswith("_posts/"):
            u = post_url(f, site_url)
            if u:
                urls.add(u)
        elif f.startswith("_prompts/"):
            urls.add(prompt_url(f, site_url))
    return urls


def resolve_submit_urls(sitemap_path: str, before_sha: str, after_sha: str, site_url: str, full: bool) -> list[str]:
    """Return post/prompt URLs to notify search engines about.

    With full=True, returns every post/prompt URL in the sitemap (for a
    one-time backfill). Otherwise returns only those whose underlying file
    changed between before_sha and after_sha.
    """
    post_prompt_urls = filter_post_prompt_urls(sitemap_urls(sitemap_path))
    if full:
        return post_prompt_urls
    changed = changed_urls(before_sha, after_sha, site_url)
    return [u for u in post_prompt_urls if u in changed]
