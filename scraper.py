"""Crawl a section of ctdata.org and save clean page text for the knowledge base.

Usage:
    python scraper.py                      # crawl the default /education section
    python scraper.py --start /education --start /census --max-pages 80

The crawler starts from one or more section pages, follows links that stay on
www.ctdata.org (section sub-pages and blog posts linked from the section), and
writes data/pages.json. External dataset links (EdSight, ArcGIS, ...) are not
crawled, but their titles and URLs are saved so the bot can point users to them.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ctdata.org"
DEFAULT_SECTIONS = ["/education"]
OUTPUT = Path(__file__).parent / "data" / "pages.json"
HEADERS = {"User-Agent": "CTData-Chatbot-Hackathon/1.0 (+educational demo)"}

# Site-wide menu/footer pages that every page links to; not section content.
NAV_PATHS = {
    "/", "/search", "/data-resources", "/data-by-topic", "/interactive-data-projects",
    "/census", "/geographic-resources", "/research", "/learn-data-skills", "/data-literacy",
    "/quantitative-data-analysis", "/analyzing-qualitative-data", "/survey-design",
    "/datastorytelling", "/data-visualization", "/explore-public-data", "/youth-data-programs",
    "/customized-data-workshops", "/events", "/event-calendar", "/equityindata", "/conferences",
    "/data-services", "/datastrategicplanning", "/consulting", "/who-we-are", "/about", "/blog",
    "/about-hdc", "/in-the-news", "/media", "/our-team", "/hiring", "/newsletter-signups",
    "/consultation", "/datahelpline", "/geospatial-data-tools-gis", "/data-resources-1",
    "/learn-data-skills-1", "/events-1", "/data-services-1", "/who-we-are-1",
}


def normalize(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/") or url


def is_internal(url: str) -> bool:
    return urlparse(url).netloc in {"www.ctdata.org", "ctdata.org"}


def extract(html: str, url: str) -> dict:
    """Return title, readable text and outgoing links for one page."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else url).replace(" — CTData", "")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="page") or soup.body or soup

    links = []
    for a in main.find_all("a", href=True):
        href = normalize(urljoin(url, a["href"]))
        label = a.get_text(" ", strip=True)
        if href.startswith("http") and label:
            links.append({"url": href, "label": label})

    # Unwrap inline tags so "see the <a>Wall Street Journal</a>, ..." stays one line.
    for tag in main.find_all(["a", "strong", "em", "b", "i", "span", "sup", "sub"]):
        tag.unwrap()
    main = BeautifulSoup(str(main), "html.parser")  # re-parse to merge adjacent strings

    # Keep one line per block so headings and list items stay readable.
    lines = [line.strip() for line in main.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return {"url": url, "title": title, "text": text, "links": links}


def crawl(sections: list[str], max_pages: int, delay: float) -> list[dict]:
    queue = [normalize(urljoin(BASE_URL, s)) for s in sections]
    section_paths = [urlparse(u).path for u in queue]
    seen: set[str] = set()
    pages: list[dict] = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  skip {url}: {exc}")
            continue

        page = extract(resp.text, url)
        page["section"] = next((p for p in section_paths if p in url), section_paths[0])
        pages.append(page)
        print(f"  [{len(pages)}] {page['title']} ({len(page['text'])} chars)")

        # Only the section pages themselves fan out; sub-pages are leaves.
        # This keeps the crawl focused on the section instead of the whole site.
        if urlparse(url).path in section_paths:
            for link in page["links"]:
                path = urlparse(link["url"]).path.rstrip("/")
                if is_internal(link["url"]) and path not in NAV_PATHS and link["url"] not in seen:
                    queue.append(link["url"])
        time.sleep(delay)

    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", action="append", help="section path, e.g. /education (repeatable)")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests (be polite)")
    args = parser.parse_args()

    sections = args.start or DEFAULT_SECTIONS
    print(f"Crawling {sections} ...")
    pages = crawl(sections, args.max_pages, args.delay)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(pages, indent=2, ensure_ascii=False))
    print(f"Saved {len(pages)} pages to {OUTPUT}")


if __name__ == "__main__":
    main()
