# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

import argparse
import sys
import requests
import lxml.etree

from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor


def insert_path_segment(url, segment):
    parsed_url = urlparse(url)
    new_path = f"/{segment}{parsed_url.path}"
    new_url = urlunparse(parsed_url._replace(path=new_path))
    return new_url


def purge_url(url):
    for encoding in ["", "gzip", "deflate", "br", "zstd"]:
        headers = {"User-Agent": "curl/7.12.1"}
        if encoding:
            headers["Accept-Encoding"] = "gzip"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            print(f"success[{encoding}]: {url}, got {res.status_code}")
        except Exception as e:
            print(f"failed, got exception: {e}", file=sys.stderr)


def get_urls(url_source: str):
    urls = []
    if url_source.endswith("xml"):
        tree = lxml.etree.parse(url_source)
        namespaces = {
            "sitemapindex": "http://www.sitemaps.org/schemas/sitemap/0.9",
        }
        for url in tree.xpath("//sitemapindex:loc/text()", namespaces=namespaces):
            urls.append(url)
    else:
        with open(url_source) as fd:
            urls.extend(
                i for i in (i.strip() for i in fd.readlines()) if not i.startswith("#")
            )
    return urls


def handle_urls(urls: list[str], segment):
    return [insert_path_segment(url, segment) for url in urls]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Purge cached URLs via Nginx cache purge segment.")
    p.add_argument("url_source", help="Path to a URL list file or sitemap.xml")
    p.add_argument("segment", help="URL path segment inserted for purge routing (e.g. purge)")
    args = p.parse_args()

    urls = get_urls(args.url_source)
    urls = handle_urls(urls, args.segment)
    print(urls)
    with ThreadPoolExecutor() as executor:
        list(executor.map(purge_url, urls))
