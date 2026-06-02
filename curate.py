import feedparser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from datetime import datetime

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
fg.link(href="https://kamilspiewak.github.io/rss-curator/")
fg.description("Curated RSS feed")

for item in unique[:25]:
    fe = fg.add_entry()
    fe.title(item["title"])
    fe.link(href=item["link"])
    fe.description(item["summary"])

fg.rss_file("docs/feed.xml")