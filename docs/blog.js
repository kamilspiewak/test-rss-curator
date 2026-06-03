const blogContainer = document.getElementById("feed_blog");
const blogParser = new RSSParser();

async function loadBlogFeed() {
    try {
        const feed = await blogParser.parseURL("blogposts.xml");

        blogContainer.innerHTML = "";

        feed.items.forEach(item => {
            const div = document.createElement("div");
            div.className = "item";

            div.innerHTML = `
                <a href="${item.link}" target="_blank">
                    <strong>${item.title}</strong>
                </a>
                <div class="meta">
                    ${item.pubDate ? new Date(item.pubDate).toLocaleString() : ""}
                </div>
                <div>
                    ${item.contentSnippet || item.content || item.summary || ""}
                </div>
            `;

            blogContainer.appendChild(div);
        });

    } catch (err) {
        console.error("Blog feed error:", err);
        blogContainer.innerHTML = "<p>Failed to load blog posts</p>";
    }
}

// load on page start
loadBlogFeed();