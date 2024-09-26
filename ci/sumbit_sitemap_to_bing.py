# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

import sys, re, json
from urllib.parse import urlparse
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
        "keyLocation": key_location,
        "urlList": url_list,
    }
    return json.dumps(data)


if __name__ == "__main__":
    should_sumbited_urls = get_urls(
        sys.argv[1], sys.argv[3], host=None if len(sys.argv) <= 4 else sys.argv[4]
    )
    print(should_sumbited_urls)
    print(submit_to_bing(sys.argv[2], should_sumbited_urls))
