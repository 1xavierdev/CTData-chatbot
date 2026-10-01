"""Crawl a section of ctdata.org and save clean page text for the knowledge base.

Usage:
    python scraper.py                      # crawl /data-by-topic, every topic page and what they link to
    python scraper.py --start /education --depth 1

The crawler starts from one or more pages, follows links that stay on www.ctdata.org
(topic pages, then the blog posts and pages they link to, up to --depth hops), and
writes data/pages.json. External dataset links (ArcGIS, ...) are not crawled,
but their titles and URLs are saved so the bot can point users to them.

EdSight (public-edsight.ct.gov) dataset links are the exception: each EdSight page
embeds a report with the statewide trend table, so we fetch that table and save it
as its own page. That lets the bot answer "what is the chronic absenteeism rate?"
with real numbers instead of only a link.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ctdata.org"
# Data by Topic links every topic page (Education, Health, Housing, ...); depth 2 also takes in the
# blog posts and other ctdata.org pages each topic page links to.
DEFAULT_SECTIONS = ["/data-by-topic"]
EDSIGHT_HOST = "public-edsight.ct.gov"
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
    parts = urlparse(url)
    if parts.netloc in {"www.ctdata.org", "ctdata.org"}:  # one spelling per page: https://www.ctdata.org/...
        url = parts._replace(scheme="https", netloc="www.ctdata.org").geturl()
    return url.rstrip("/") or url


# Downloads (data snapshots, spreadsheets) aren't web pages; they stay as links only.
FILE_EXTENSIONS = (".pdf", ".xlsx", ".xls", ".csv", ".zip", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg")


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


YEAR = re.compile(r"\b(19|20)\d\d-\d\d\b")


def table_grid(table) -> list[tuple[bool, list[str]]]:
    """Expand rowspans/colspans so every row has one text per column. Returns (is_header, texts) rows."""
    grid, carried = [], {}  # carried: column -> [rows left, text] from a rowspan above
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        row, col = [], 0

        def fill_carried():
            nonlocal col
            while col in carried:
                row.append(carried[col][1])
                carried[col][0] -= 1
                if not carried[col][0]:
                    del carried[col]
                col += 1

        for cell in cells:
            fill_carried()
            text = cell.get_text(" ", strip=True)
            for _ in range(int(cell.get("colspan") or 1)):
                if int(cell.get("rowspan") or 1) > 1:
                    carried[col] = [int(cell["rowspan"]) - 1, text]
                row.append(text)
                col += 1
        fill_carried()
        grid.append((all(c.name == "th" for c in cells), row))
    return grid


def table_records(table) -> tuple[list[str], list[dict]]:
    """Split one EdSight report table into its notes and one record per row, school year and measure,
    e.g. {"name": "State of Connecticut", "year": "2025-26", "measure": "Chronically Absent %", "value": "16.4"}."""
    headers, notes, records = [], [], []
    for is_header, row in table_grid(table):
        if len(row) == 1:  # title/notes row
            if row[0] and row[0] != "Export .csv file":
                notes.append(row[0])
        elif is_header:
            headers.append(row)
        elif any(row[1:]):
            labels = [" ".join(dict.fromkeys(h[i] for h in headers if i < len(h) and h[i])) for i in range(len(row))]
            names = [value for label, value in zip(labels, row) if value and not YEAR.search(label)]
            for label, value in zip(labels, row):
                if year := YEAR.search(label):
                    measure = YEAR.sub("", label).replace("School Year", "").replace("by Year", "").replace("Year", "")
                    records.append({"name": ", ".join(names), "year": year.group(0),
                                    "measure": " ".join(measure.split()), "value": value})
    return notes, records


def table_lines(table) -> list[str]:
    """Flatten one EdSight report table into one readable line per row and school year,
    e.g. "State of Connecticut, 2025-26: Chronically Absent Student Count 77,527; Chronically Absent % 16.4"."""
    notes, records = table_records(table)
    by_row: dict[tuple[str, str], list[str]] = {}
    for r in records:
        by_row.setdefault((r["name"], r["year"]), []).append(f"{r['measure']} {r['value']}".strip())
    return notes + [f"{name}, {year}: " + "; ".join(values) for (name, year), values in by_row.items()]


def edsight_report(url: str, label: str) -> dict | None:
    """Fetch an EdSight dataset page and the statewide report table it embeds."""
    try:
        page = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=30).text, "html.parser")
        frame = next((f["src"] for f in page.find_all("iframe") if "SASStoredProcess" in f.get("src", "")), None)
        if not frame:
            return None
        report = BeautifulSoup(requests.get(frame, headers=HEADERS, timeout=60).text, "html.parser")
    except requests.RequestException as exc:
        print(f"  skip {url}: {exc}")
        return None

    lines: list[str] = []
    records: list[dict] = []
    for table in report.find_all("table"):
        if table.find("table") is None:  # innermost tables only; the outer ones just repeat them
            lines += [line for line in table_lines(table) if line not in lines]
            records += [r for r in table_records(table)[1] if r not in records]
    if not any(":" in line for line in lines):
        return None
    title = page.title.get_text(strip=True) if page.title else label
    text = "\n".join([
        f"{title}: Connecticut statewide trend from EdSight, the CT State Department of Education data portal.",
        *lines,
        f"Breakdowns by district, school and student group are available at {url}",
    ])
    # "records" keeps the numbers structured so the chatbot can chart them (see charts.py).
    return {"url": url, "title": f"EdSight: {title} (statewide)", "text": text, "links": [], "section": "/edsight",
            "records": records}


def fetch_edsight(pages: list[dict], delay: float) -> list[dict]:
    links = {}
    for page in pages:
        for link in page["links"]:
            if urlparse(link["url"]).netloc == EDSIGHT_HOST:
                links.setdefault(link["url"], link["label"])
    reports = []
    for url, label in links.items():
        if report := edsight_report(url, label):
            reports.append(report)
            print(f"  [edsight] {report['title']} ({len(report['text'])} chars)")
        time.sleep(delay)
    return reports


def crawl(sections: list[str], max_pages: int, delay: float, depth: int = 1) -> list[dict]:
    """Breadth-first crawl of www.ctdata.org from the start pages, following internal links up to `depth` hops.

    Each page is tagged with a "section": the start page's path for the start page itself and, for
    everything below it, the path of the first-level page it was reached through (e.g. /data-by-topic
    -> /health -> a blog post: section "/health").
    """
    queue = [(normalize(urljoin(BASE_URL, s)), 0, "") for s in sections]
    seen: set[str] = set()
    seen_text: set[int] = set()  # the same page can live at two URLs (e.g. /covid-update and a blog post)
    pages: list[dict] = []

    while queue and len(pages) < max_pages:
        url, level, section = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  skip {url}: {exc}")
            continue
        final = normalize(resp.url)
        if "text/html" not in resp.headers.get("Content-Type", "") or (final != url and final in seen):
            continue
        seen.add(final)

        page = extract(resp.text, url)
        if hash(page["text"]) in seen_text:
            continue
        seen_text.add(hash(page["text"]))
        page["section"] = section or urlparse(url).path
        pages.append(page)
        print(f"  [{len(pages)}] {page['section']}: {page['title']} ({len(page['text'])} chars)")

        # Deeper pages are leaves, which keeps the crawl on the section instead of the whole site.
        if level < depth:
            for link in page["links"]:
                path = urlparse(link["url"]).path.rstrip("/") or "/"
                if (is_internal(link["url"]) and path not in NAV_PATHS and link["url"] not in seen
                        and not path.startswith(("/blog/category/", "/blog/tag/", "/s/"))
                        and not path.lower().endswith(FILE_EXTENSIONS)):
                    queue.append((link["url"], level + 1, section or (path if depth > 1 else page["section"])))
        time.sleep(delay)

    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", action="append", help="section path, e.g. /education (repeatable)")
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--depth", type=int, default=2, help="link hops to follow from the start pages")
    parser.add_argument("--edsight-only", action="store_true", help="re-fetch only the EdSight tables in data/pages.json")
    parser.add_argument("--no-edsight", action="store_true", help="don't fetch EdSight report tables")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests (be polite)")
    args = parser.parse_args()

    if args.edsight_only:
        pages = [p for p in json.loads(OUTPUT.read_text()) if p.get("section") != "/edsight"]
        print(f"Refreshing EdSight tables linked from {len(pages)} saved pages ...")
        pages += fetch_edsight(pages, args.delay)
    else:
        sections = args.start or DEFAULT_SECTIONS
        print(f"Crawling {sections} ...")
        pages = crawl(sections, args.max_pages, args.delay, args.depth)
        if not args.no_edsight:
            pages += fetch_edsight(pages, args.delay)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(pages, indent=2, ensure_ascii=False))
    print(f"Saved {len(pages)} pages to {OUTPUT}")


if __name__ == "__main__":
    main()
