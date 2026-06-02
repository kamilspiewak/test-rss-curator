const CORS_PROXY = ""; // GitHub Pages usually doesn't need one if same domain

const FEED_URL = "feed.xml";

const parser = new RSSParser();
let allItems = [];

async function loadFeed() {
  const feed = await parser.parseURL(FEED_URL);

  allItems = feed.items.map(item => ({
    title: item.title,
    link: item.link,
    content: item.contentSnippet || item.content || "",
    date: item.pubDate || ""
  }));

  render(allItems);
}

function render(items) {
  const container = document.getElementById("feed");
  container.innerHTML = "";

  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "item";

    div.innerHTML = `
      <a href="${item.link}" target="_blank">
        <h3>${item.title}</h3>
      </a>
      <div class="meta">${item.date}</div>
      <p>${item.content}</p>
    `;

    container.appendChild(div);
  });
}

document.getElementById("filter").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase();

  const filtered = allItems.filter(item =>
    item.title.toLowerCase().includes(q) ||
    item.content.toLowerCase().includes(q)
  );

  render(filtered);
});

loadFeed();