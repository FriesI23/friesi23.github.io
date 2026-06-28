"""Submit changed post/prompt URLs to the Google Indexing API.

Only request publishes for posts and prompts (the two collections worth
notifying Google about) using the file changes between before_sha and
after_sha. Use --full to submit every post/prompt URL found in the sitemap
instead, e.g. for a one-time historical backfill.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import lxml.etree
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/indexing"
PUBLISH_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"

# Mirrors permalink rules in _config.yml
_POST_PATH = re.compile(r"^/post/\d{6}/[^/]+/?$")
_PROMPT_PATH = re.compile(r"^/prompts/[^/]+$")  # excludes the bare /prompts/ index


def _sitemap_urls(sitemap_path: str) -> list[str]:
    tree = lxml.etree.parse(sitemap_path)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return tree.xpath("//s:url/s:loc/text()", namespaces=ns)


def _filter_post_prompt_urls(urls: list[str]) -> list[str]:
    return [u for u in urls if _POST_PATH.match(urlparse(u).path) or _PROMPT_PATH.match(urlparse(u).path)]


def _changed_files(before_sha: str, after_sha: str) -> list[str]:
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


def _post_url(filepath: str, site_url: str) -> str | None:
    stem = Path(filepath).stem
    m = re.match(r"^(\d{4})-(\d{2})-\d{2}-(.+)$", stem)
    if not m:
        return None
    year, month, slug = m.groups()
    return f"{site_url}/post/{year}{month}/{slug}"


def _prompt_url(filepath: str, site_url: str) -> str:
    rel = Path(filepath).relative_to("_prompts").with_suffix("")
    return f"{site_url}/prompts/{rel}"


def _changed_urls(before_sha: str, after_sha: str, site_url: str) -> set[str]:
    urls: set[str] = set()
    for f in _changed_files(before_sha, after_sha):
        if f.startswith("_posts/"):
            u = _post_url(f, site_url)
            if u:
                urls.add(u)
        elif f.startswith("_prompts/"):
            urls.add(_prompt_url(f, site_url))
    return urls


def _access_token(key_path: str) -> str:
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=[SCOPE])
    creds.refresh(Request())
    return creds.token


def _publish(token: str, url: str) -> requests.Response:
    return requests.post(
        PUBLISH_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"url": url, "type": "URL_UPDATED"},
        timeout=10,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Submit changed post/prompt URLs to the Google Indexing API.")
    p.add_argument("sitemap", help="Path to sitemap.xml")
    p.add_argument("service_account_key", help="Path to the Google service account JSON key file")
    p.add_argument("--before-sha", default="0" * 40, help="SHA of the commit before the push")
    p.add_argument("--after-sha", default="HEAD", help="SHA of the current (head) commit")
    p.add_argument("--site-url", default="https://friesi23.icu")
    p.add_argument(
        "--full",
        action="store_true",
        help="Submit every post/prompt URL in the sitemap, ignoring the git diff (one-time backfill)",
    )
    args = p.parse_args()

    post_prompt_urls = _filter_post_prompt_urls(_sitemap_urls(args.sitemap))

    if args.full:
        submit_urls = post_prompt_urls
    else:
        changed = _changed_urls(args.before_sha, args.after_sha, args.site_url)
        submit_urls = [u for u in post_prompt_urls if u in changed]

    if not submit_urls:
        print("No post/prompt URLs to submit to Google.")
        sys.exit(0)

    token = _access_token(args.service_account_key)
    failures = 0
    for url in submit_urls:
        res = _publish(token, url)
        print(url, res.status_code, res.text)
        if res.status_code != 200:
            failures += 1

    if failures:
        sys.exit(1)
