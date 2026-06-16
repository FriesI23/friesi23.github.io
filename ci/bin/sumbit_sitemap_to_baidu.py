# Copyright @Myth 2024
# see: https://myth.cx/p/hugo-auto-submit-baidu/

import argparse
import requests
import lxml.etree


def submit_to_baidu(api_url, submit_urls):
    headers = {
        "User-Agent": "curl/7.12.1",
        "Host": "data.zz.baidu.com",
        "Content-Type": "text/plain",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Length": str(len(submit_urls)),
    }
    res = requests.post(api_url, headers=headers, data=submit_urls, timeout=10)
    return res.text


def get_urls(sitemap_path):
    tree = lxml.etree.parse(sitemap_path)
    namespaces = {
        "sitemapindex": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }
    urls = ""
    for url in tree.xpath("//sitemapindex:loc/text()", namespaces=namespaces):
        urls += url + "\n"
    return urls


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Submit sitemap URLs to Baidu.")
    p.add_argument("sitemap", help="Path to sitemap.xml")
    p.add_argument("api_url", help="Baidu sitemap submission API URL (including token)")
    args = p.parse_args()

    should_submitted_urls = get_urls(args.sitemap)
    print(should_submitted_urls)
    print(submit_to_baidu(args.api_url, should_submitted_urls))
