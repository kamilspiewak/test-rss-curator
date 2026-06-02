import feedparser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch_html(url, timeout=15):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_text(html_text):
    return BeautifulSoup(html_text or "", "html.parser").get_text(" ", strip=True)


def parse_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass

    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def get_entry_date(entry):
    for key in ["published_parsed", "updated_parsed", "created_parsed"]:
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                return None

    for key in ["published", "updated", "created"]:
        parsed = parse_datetime(entry.get(key))
        if parsed:
            return parsed

    return None


def extract_title(element):
    header = element.find(["h1", "h2", "h3"])
    if header and header.get_text(strip=True):
        return header.get_text(" ", strip=True)

    link = element.find("a", href=True)
    if link and link.get_text(strip=True):
        return link.get_text(" ", strip=True)

    return element.get_text(" ", strip=True)


def extract_link(element, base_url):
    if element.name == "a" and element.get("href"):
        return urljoin(base_url, element.get("href"))

    link = element.find("a", href=True)
    if link:
        return urljoin(base_url, link["href"])

    return None


def extract_summary(element):
    paragraph = element.find("p")
    if paragraph and paragraph.get_text(strip=True):
        return paragraph.get_text(" ", strip=True)

    text = element.get_text(" ", strip=True)
    return (text[:280] + "...") if len(text) > 280 else text


def extract_date(element):
    time_tag = element.find("time")
    if time_tag:
        date_value = time_tag.get("datetime") or time_tag.get_text(strip=True)
        return parse_datetime(date_value)

    for attr in ["date", "datetime", "pubdate"]:
        if element.has_attr(attr):
            return parse_datetime(element.get(attr))

    return None


def scrape_blog(url):
    try:
        html = fetch_html(url)
    except (HTTPError, URLError, ValueError):
        return []

    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.find_all("article")

    if not candidates:
        for selector in [".post", ".entry", ".article", ".blog-post", ".post-preview", ".card"]:
            candidates = soup.select(selector)
            if candidates:
                break

    if not candidates:
        container = soup.find("main") or soup.body or soup
        candidates = container.find_all(["article", "section", "div", "li"], limit=25)

    results = []
    seen_links = set()

    for candidate in candidates:
        title = extract_title(candidate)
        link = extract_link(candidate, url)
        summary = extract_summary(candidate)
        date = extract_date(candidate)

        if not title or not link:
            continue

        if link in seen_links:
            continue

        seen_links.add(link)
        results.append({
            "title": title,
            "link": link,
            "summary": summary,
            "date": date,
        })

        if len(results) >= 5:
            break

    return results


def collect_items(feed_urls):
    items = []

    for url in feed_urls:
        feed = feedparser.parse(url)

        if feed.entries:
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = normalize_text(entry.get("summary", entry.get("description", entry.get("content", ""))))
                date = get_entry_date(entry)

                if not title or not link:
                    continue

                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "date": date,
                })
        else:
            items.extend(scrape_blog(url))

    return items


def dedupe_items(items):
    seen = set()
    unique = []

    for item in items:
        if item.get("link") and item["link"] not in seen:
            seen.add(item["link"])
            unique.append(item)

    return unique


def build_feed(items, output_path="docs/feed.xml"):
    fg = FeedGenerator()
    fg.title("My Curated Feed")
    fg.link(href="https://kamilspiewak.github.io/rss-curator/", rel="alternate")
    fg.description("Curated RSS feed")
    fg.language("en")

    for item in items[:25]:
        fe = fg.add_entry()
        fe.id(item["link"])
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.description(item["summary"])
        if item.get("date"):
            fe.pubDate(item["date"])

    fg.rss_file(output_path)


if __name__ == "__main__":
    feed_urls = [line.strip() for line in open("feeds.txt") if line.strip()]
    items = collect_items(feed_urls)
    unique_items = dedupe_items(items)
    build_feed(unique_items)
