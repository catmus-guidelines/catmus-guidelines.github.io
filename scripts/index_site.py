"""Build the client-side search index (json/index.json) for minisearch.

Indexes the pages the manifest actually produced, rather than globbing a
directory, and stamps a stable id onto each indexed block in the emitted HTML so
search results can deep-link to it.

Two things the previous version got wrong, both of which broke result links:
  * `title` was the output filename ("7_functionnal_sign"), not the page title
  * `url` was a repo-relative path with no leading slash, so following a result
    from a nested page resolved against the wrong directory
"""

import json
import os
import re

from bs4 import BeautifulSoup

WHITESPACE = re.compile(r"\s+")

# Blocks worth indexing: prose and standalone lists. Table cells are excluded
# because the character table would otherwise flood the index with single glyphs.
INDEXED = ("p", "li", "dd", "blockquote")

MIN_LENGTH = 25


def build_index(out_root, pages):
    """Index the built pages in place, writing out_root/json/index.json."""
    records = []

    for page in pages:
        path = os.path.join(out_root, page.out_path)
        if not os.path.isfile(path):
            continue

        with open(path, encoding="utf-8") as handle:
            soup = BeautifulSoup(handle.read(), "html.parser")

        main = soup.find(id="main") or soup
        counter = 0

        for node in main.find_all(INDEXED):
            # Skip list items that merely wrap other indexed blocks: indexing both
            # the <li> and its <p> stores the same text twice under two ids.
            if node.name == "li" and node.find("p"):
                continue

            text = WHITESPACE.sub(" ", node.get_text(" ", strip=True)).strip()
            if len(text) < MIN_LENGTH:
                continue

            counter += 1
            node_id = node.get("id") or f"idx-{page.slug}-{counter}"
            node["id"] = node_id

            records.append(
                {
                    "id": f"{page.slug}:{counter}",
                    "anchor": node_id,
                    "url": page.url,
                    "title": page.title,
                    "node": text,
                }
            )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(soup))

    destination = os.path.join(out_root, "json", "index.json")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=1, ensure_ascii=False)

    print(f"  json/index.json ({len(records)} blocks from {len(pages)} pages)")
    return records
