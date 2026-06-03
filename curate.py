import feedparser
import requests
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

feeds = open("feeds.txt").read().splitlines()

items = []

for url in feeds:
    feed = feedparser.parse(url)

    for entry in feed.entries[:5]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        summary = entry.get("summary", "")

        text = BeautifulSoup(summary, "html.parser").get_text()

        items.append({
            "title": title,
            "link": link,
            "summary": text,
        })

# dedupe by link
seen = set()
unique = []

for item in items:
    if item["link"] not in seen:
        seen.add(item["link"])
        unique.append(item)

fg = FeedGenerator()
fg.title("My Curated Feed")
fg.link(href="https://kamilspiewak.github.io/test-rss-curator/")
fg.description("Curated RSS feed")

for item in unique[:25]:
    fe = fg.add_entry()
    fe.title(item["title"])
    fe.link(href=item["link"])
    fe.description(item["summary"])

fg.rss_file("docs/feed.xml")


def load_blog_sources(file_path="blogs.txt"):
    try:
        with open(file_path, "r") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return []


def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_blog_posts(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    # heurystyka: artykuły lub linki
    for article in soup.select("article, .post, .entry, .blog-post, .news-item, .thumbnail-article"):
        title_tag = article.find(["h1", "h2", "h3"])
        link_tag = article.find("a")

        if title_tag and link_tag:
            title = title_tag.get_text(strip=True)
            link = link_tag.get("href")

            if link and not link.startswith("http"):
                link = base_url.rstrip("/") + "/" + link.lstrip("/")
            # attempt to extract a publish date from common places
            pub_date = None
            date_text = None
            time_tag = article.find("time")
            if time_tag:
                date_text = time_tag.get("datetime") or time_tag.get_text(strip=True)
            else:
                meta = (article.find("meta", {"property": "article:published_time"}) or
                        article.find("meta", {"name": "date"}) or
                        article.find("meta", {"name": "pubdate"}))
                if meta:
                    date_text = meta.get("content") or meta.get("value")

            if date_text and date_parser:
                try:
                    pub_date = date_parser.parse(date_text)
                except Exception:
                    pub_date = None

            # remove the title element so it doesn't appear in the description
            try:
                title_tag.decompose()
            except Exception:
                pass

            # remove some common noisy elements that pollute the summary
            for selector in ["script", "style", "img", "svg", ".share", ".tags"]:
                for el in article.select(selector):
                    try:
                        el.decompose()
                    except Exception:
                        pass

            # grab remaining text as description
            description = article.get_text(" ", strip=True)[:300]

            posts.append({
                "title": title,
                "link": link,
                "summary": description,
                "date": pub_date
            })

    return posts


def collect_blog_posts():
    blog_urls = load_blog_sources()
    all_posts = []

    for url in blog_urls:
        html = fetch_html(url)
        if not html:
            continue

        posts = parse_blog_posts(html, url)
        # sort posts by date (newest first). Posts without date go to the end.
        posts_sorted = sorted(posts, key=lambda p: p.get('date') or datetime.min, reverse=True)
        # limit to 5 items per source
        all_posts.extend(posts_sorted[:5])

    return all_posts


def generate_blog_rss(posts, output_file="docs/blogposts.xml"):
    fg = FeedGenerator()
    fg.title("Blog Posts Feed")
    fg.link(href="https://kamilspiewak.github.io/test-rss-curator/")
    fg.description("Scraped blog posts")

    seen = set()

    for item in posts:
        if item["link"] in seen:
            continue
        seen.add(item["link"])

        fe = fg.add_entry()
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.description(item["summary"])
        if item.get("date"):
            try:
                fe.pubDate(item.get("date"))
            except Exception:
                pass

    fg.rss_file(output_file)


# --- BLOG SCRAPING FLOW ---
blog_posts = collect_blog_posts()
generate_blog_rss(blog_posts)
