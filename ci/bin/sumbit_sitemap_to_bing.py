# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

"""Submit changed post/prompt URLs to Bing via IndexNow.

IndexNow is meant to notify search engines about new/updated content, not to
resubmit the whole site on every push, so only post/prompt URLs whose file
changed between before_sha and after_sha are sent. Use --full to submit
every post/prompt URL found in the sitemap instead, e.g. for a one-time
historical backfill.
"""

import argparse
import json
import re
from urllib.parse import urlparse, urlunparse

import requests
from sitemap_diff import resolve_submit_urls


def build_payload(submit_urls, key_location, host=None):
    return {
        "host": urlparse(key_location).netloc if host is None else host,
        "key": re.search(r"/([^/]+)\.txt$", key_location).group(1),
        "keyLocation": (
            key_location if host is None else urlunparse(urlparse(key_location)._replace(netloc=host))
        ),
        "urlList": submit_urls,
    }


def submit_to_bing(api_url, payload):
    data = json.dumps(payload)
    headers = {
        "User-Agent": "curl/7.12.1",
        "Host": "api.indexnow.org",
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(data)),
    }
    res = requests.post(api_url, headers=headers, data=data, timeout=10)
    return res


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Submit changed post/prompt URLs to Bing via IndexNow.")
    p.add_argument("sitemap", help="Path to sitemap.xml")
    p.add_argument("api_url", help="IndexNow API URL (e.g. http://api.indexnow.org/IndexNow)")
    p.add_argument("key_location", help="Full URL to the IndexNow key file")
    p.add_argument("host", nargs="?", default=None, help="Override host extracted from key_location (optional)")
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
        print("No post/prompt URLs to submit to Bing.")
        raise SystemExit(0)

    payload = build_payload(submit_urls, args.key_location, host=args.host)
    print(json.dumps(payload))
    result = submit_to_bing(args.api_url, payload)
    print(result)
    print(result.text)
