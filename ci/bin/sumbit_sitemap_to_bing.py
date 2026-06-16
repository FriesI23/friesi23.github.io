# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

import argparse
import json
import re
from urllib.parse import urlparse, urlunparse
import requests
import lxml.etree


def submit_to_bing(api_url, submit_urls):
    headers = {
        "User-Agent": "curl/7.12.1",
        "Host": "api.indexnow.org",
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(submit_urls)),
    }
    res = requests.post(api_url, headers=headers, data=submit_urls, timeout=10)
    return res


def get_urls(sitemap_path, key_location, host=None):
    tree = lxml.etree.parse(sitemap_path)
    namespaces = {
        "sitemapindex": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }
    url_list = []
    for url in tree.xpath("//sitemapindex:loc/text()", namespaces=namespaces):
        url_list.append(url)
    data = {
        "host": urlparse(key_location).netloc if host is None else host,
        "key": re.search(r"/([^/]+)\.txt$", key_location).group(1),
        "keyLocation": (
            key_location
            if host is None
            else urlunparse(urlparse(key_location)._replace(netloc=host))
        ),
        "urlList": url_list,
    }
    return json.dumps(data)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Submit sitemap URLs to Bing via IndexNow.")
    p.add_argument("sitemap", help="Path to sitemap.xml")
    p.add_argument("api_url", help="IndexNow API URL (e.g. http://api.indexnow.org/IndexNow)")
    p.add_argument("key_location", help="Full URL to the IndexNow key file")
    p.add_argument("host", nargs="?", default=None, help="Override host extracted from key_location (optional)")
    args = p.parse_args()

    should_submitted_urls = get_urls(args.sitemap, args.key_location, host=args.host)
    print(should_submitted_urls)
    result = submit_to_bing(args.api_url, should_submitted_urls)
    print(result)
    print(result.text)
