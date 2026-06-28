"""Submit changed post/prompt URLs to the Google Indexing API.

Only request publishes for posts and prompts (the two collections worth
notifying Google about) using the file changes between before_sha and
after_sha. Use --full to submit every post/prompt URL found in the sitemap
instead, e.g. for a one-time historical backfill.
"""

import argparse
import sys

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sitemap_diff import resolve_submit_urls

SCOPE = "https://www.googleapis.com/auth/indexing"
PUBLISH_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"


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

    submit_urls = resolve_submit_urls(args.sitemap, args.before_sha, args.after_sha, args.site_url, args.full)

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
