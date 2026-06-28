# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

"""Submit changed post/prompt URLs to Baidu's link submission API.

Baidu's API-submission quota is shared across all submissions and is easily
exhausted by resubmitting unchanged links, so only post/prompt URLs whose
file changed between before_sha and after_sha are sent. Use --full to submit
every post/prompt URL found in the sitemap instead, e.g. for a one-time
historical backfill.
"""

import argparse

import requests
from sitemap_diff import resolve_submit_urls


def submit_to_baidu(api_url, submit_urls):
    data = "\n".join(submit_urls)
    headers = {
        "User-Agent": "curl/7.12.1",
        "Host": "data.zz.baidu.com",
        "Content-Type": "text/plain",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Length": str(len(data)),
    }
    res = requests.post(api_url, headers=headers, data=data, timeout=10)
    return res.text


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Submit changed post/prompt URLs to Baidu.")
    p.add_argument("sitemap", help="Path to sitemap.xml")
    p.add_argument("api_url", help="Baidu sitemap submission API URL (including token)")
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
        print("No post/prompt URLs to submit to Baidu.")
        raise SystemExit(0)

    print("\n".join(submit_urls))
    print(submit_to_baidu(args.api_url, submit_urls))
