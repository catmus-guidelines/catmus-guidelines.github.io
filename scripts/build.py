#!/usr/bin/env python3
"""Build the CATMuS guidelines site into _site/.

    python3 scripts/build.py                  # build once
    python3 scripts/build.py --serve           # build, then serve on :8000
    python3 scripts/build.py --serve --watch   # rebuild on change
    python3 scripts/build.py --no-pdf          # skip the (slow) PDF step

Nothing is written outside _site/, which is gitignored: the repository never
contains generated files, and CI publishes _site/ alone.
"""

import argparse
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import sys
import tempfile
import time

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from marko import Markdown

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import catmus
import characters
import index_site
import pdf

ROOT = catmus.ROOT
OUT = catmus.OUT
PDF_NAME = "catmus-guidelines.pdf"
PDF_PATH = os.path.join(OUT, PDF_NAME)

# Static trees copied verbatim into _site.
# The two image entries are what make the authors' source-relative image paths
# resolve: content written in data/guidelines/en/ uses `../img/x.png` and
# `../../examples/y.png`, so the images must sit at the same relative offsets
# from the emitted html/guidelines/en/ pages.
STATIC_TREES = [
    ("assets", "assets"),
    ("keyboards", "keyboards"),
    (os.path.join("data", "guidelines", "img"), os.path.join("html", "guidelines", "img")),
    (os.path.join("data", "examples"), os.path.join("html", "examples")),
]


# --------------------------------------------------------------------------- #
# markdown
# --------------------------------------------------------------------------- #

def render_markdown(path):
    """Markdown source -> HTML fragment, with the footnote block tidied."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    _check_tables(path, text)
    _check_spans(path, text)
    # "gfm" is what parses the pipe tables the sources are full of; without it
    # they render as literal rows of pipes.
    html = Markdown(extensions=["gfm", "footnote"]).convert(text)
    # The template supplies its own rule under the <h1>; the leading <hr> that
    # several sources start with would double it.
    html = html.replace("<hr />", "")

    soup = BeautifulSoup(html, "html.parser")
    _demote_top_headings(soup)
    _move_notes_heading_into_footnotes(soup)
    _add_heading_ids(soup)
    _promote_repeated_headers(soup)
    _wrap_wide_tables(soup)
    return str(soup)


def _check_tables(path, text):
    """Warn about pipe tables that will not be parsed as tables.

    A table header row glued to the paragraph above it is read as lazy
    continuation of that paragraph, so the whole table renders as literal pipes.
    That failure is invisible in the source and easy to reintroduce.
    """
    lines = text.split("\n")
    for number, line in enumerate(lines):
        if not re.match(r"^\s*\|.*\|\s*$", line):
            continue
        previous = lines[number - 1] if number else ""
        if previous.strip() and not previous.lstrip().startswith("|"):
            print(
                f"  ! {os.path.relpath(path, ROOT)}:{number + 1}: table header needs a "
                f"blank line above it, or it will render as text"
            )


def _check_spans(path, text):
    """Warn about unbalanced <span> tags.

    A missing `</span>` is not visibly wrong in the source, but the parser closes
    it at the end of the file, so everything that follows is absorbed into the
    span. Three of these were live on the site, one swallowing half a page.
    """
    depth, opened = 0, None
    for number, line in enumerate(text.split("\n"), 1):
        for match in re.finditer(r"</?span", line):
            if match.group(0) == "<span":
                if depth == 0:
                    opened = number
                depth += 1
            else:
                depth -= 1
                if depth < 0:
                    print(
                        f"  ! {os.path.relpath(path, ROOT)}:{number}: </span> with no "
                        f"matching <span>"
                    )
                    depth = 0
        # A span never crosses a blank line: markdown would have closed the
        # paragraph, so an open span at that point is a missing tag.
        if depth and not line.strip():
            print(
                f"  ! {os.path.relpath(path, ROOT)}:{opened}: <span> is never closed "
                f"(still open at line {number})"
            )
            depth = 0
    if depth:
        print(f"  ! {os.path.relpath(path, ROOT)}:{opened}: <span> is never closed")


def _demote_top_headings(soup):
    """Push a source-level <h1> down to <h2>.

    The page's <h1> is the manifest title, supplied by the template. Most sources
    start at `##`, but 4_abbreviations.md opens with `# Abbreviations`, which
    printed the title twice on the page and produced a duplicate empty chapter in
    the PDF. Demoting also keeps one <h1> per page, which is what screen readers
    and search engines expect.
    """
    for heading in soup.find_all("h1"):
        heading.name = "h2"


def _move_notes_heading_into_footnotes(soup):
    """Put the "Notes" heading inside the footnotes block it introduces.

    Authors write a `## Notes` heading before the footnote definitions; marko
    emits the generated footnote <div> separately, so without this the heading
    floats above an unrelated block.
    """
    footnotes = soup.find("div", class_="footnotes")
    if footnotes is None:
        return
    for level in ("h2", "h3"):
        for heading in soup.find_all(level):
            if heading.get_text(strip=True) == "Notes":
                heading.extract()
                new = soup.new_tag("h2")
                new.string = "Notes"
                footnotes.insert(0, new)
                return


def rewrite_internal_links(html, pages):
    """Point in-content links at the page's real URL.

    Authors link to pages by their markdown source name and without a leading
    slash, e.g. `html/guidelines/en/9_tools.html`. Both halves of that are wrong
    once the manifest owns routing: the numeric prefix is not in the output name,
    `9_tools` is emitted at the site root, and a relative path resolves against
    whatever directory the linking page happens to sit in.

    Rather than push that bookkeeping onto authors, resolve any link whose final
    segment matches a known source stem or slug to that page's canonical URL.
    """
    lookup = {}
    for page in pages:
        stem = os.path.splitext(page.source)[0]
        lookup[f"{stem}.html"] = page.url
        lookup[f"{stem}.md"] = page.url
        lookup[f"{page.slug}.html"] = page.url

    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path, _, fragment = href.partition("#")
        target = lookup.get(os.path.basename(path))
        if target:
            anchor["href"] = target + (f"#{fragment}" if fragment else "")
    return str(soup)


def _add_heading_ids(soup):
    """Give every heading a stable id.

    assets/js/heading_links.js turns each heading into a self-link using its id;
    marko emits none, so every one of those links pointed at "#null". They are
    also what makes a search result able to land on the right section, and what
    people paste when citing a specific rule.
    """
    used = {}
    for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for heading in soup.find_all(level):
            if heading.get("id"):
                continue
            base = catmus.slugify(heading.get_text(" ", strip=True), fallback="section")
            slug = base
            if slug in used:
                used[base] += 1
                slug = f"{base}-{used[base]}"
            else:
                used[base] = 1
            heading["id"] = slug


TRANSCRIPTION = "transcription"


def _is_caption_row(cells):
    """A row that says "Transcription" is a caption, not data.

    Markdown allows one header row per table, but the authors stack several
    manuscript examples in a single table and re-state the
    "<shelfmark> | Transcription" caption before each one. Those arrive as
    ordinary body cells, indistinguishable from an actual transcription.
    """
    return any(cell.get_text(" ", strip=True).lower() == TRANSCRIPTION for cell in cells)


def _promote_repeated_headers(soup):
    """Render the repeated caption rows inside a table body as headers."""
    for table in soup.find_all("table"):
        if table.get("id") == "character_table":
            continue
        body = table.find("tbody")
        if body is None:
            continue

        for row in body.find_all("tr"):
            cells = row.find_all("td")
            if not cells or not _is_caption_row(cells):
                continue
            row["class"] = row.get("class", []) + ["caption-row"]
            for cell in cells:
                cell.name = "th"
                cell["scope"] = "col"


def _wrap_wide_tables(soup):
    """Give every table its own horizontal scroll container.

    The character table is seven columns of glyphs and images; without this it
    forces the whole page to scroll sideways on narrow screens.
    """
    for table in soup.find_all("table"):
        # A "Transcription" column means a manuscript example facing its reading:
        # equal columns and a smaller face, since the scan would otherwise claim
        # the width and the transcription is a supporting text, not body copy.
        # Flagged here rather than in CSS, which cannot ask what a table holds.
        if table.get("id") != "character_table" and _is_caption_row(
            table.find_all(["th", "td"])
        ):
            table["class"] = table.get("class", []) + ["transcription-table"]

        if table.find_parent("div", class_="table-scroll"):
            continue
        wrapper = soup.new_tag("div")
        wrapper["class"] = "table-scroll"
        table.wrap(wrapper)


# --------------------------------------------------------------------------- #
# keyboards
# --------------------------------------------------------------------------- #

def render_keyboard_tables(html, out_root=None):
    """Expand `<div class="json" data-target="...">` into a keyboard grid.

    Rebuilt from the original write_json_tables(), with two fixes: the heading
    used to be the raw file path, and the function returned None while its
    result was assigned back to the page path.
    """
    soup = BeautifulSoup(html, "html.parser")

    for holder in soup.select("div.json"):
        target = holder.get("data-target")
        if not target:
            continue
        source = os.path.join(ROOT, target)
        if not os.path.isfile(source):
            print(f"  ! keyboard JSON not found: {target}", file=sys.stderr)
            continue

        with open(source, encoding="utf-8") as handle:
            keyboard = json.load(handle)

        characters = keyboard.get("characters", [])
        if not characters:
            continue

        rows = max(c["row"] for c in characters) + 1
        cols = max(c["column"] for c in characters) + 1
        grid = [[None] * cols for _ in range(rows)]
        for char in characters:
            grid[char["row"]][char["column"]] = char

        heading = soup.new_tag("h3")
        heading.string = keyboard.get("name", target)
        holder.append(heading)

        table = soup.new_tag("table")
        table["class"] = "keyboard"
        body = soup.new_tag("tbody")
        table.append(body)
        for row in grid:
            tr = soup.new_tag("tr")
            for char in row:
                td = soup.new_tag("td")
                if char is not None:
                    kbd = soup.new_tag("kbd")
                    kbd.string = char["character"]
                    # The legend is the only thing that makes a combining mark
                    # identifiable, so expose it to assistive tech too.
                    kbd["title"] = char.get("legend", "")
                    kbd["aria-label"] = char.get("legend", "")
                    td.append(kbd)
                else:
                    td["class"] = "empty"
                tr.append(td)
            body.append(tr)

        wrapper = soup.new_tag("div")
        wrapper["class"] = "table-scroll"
        wrapper.append(table)
        holder.append(wrapper)

        download = soup.new_tag("p")
        download["class"] = "keyboard-download"
        link = soup.new_tag("a", href="/" + target.replace(os.sep, "/"))
        link["download"] = os.path.basename(target)
        link.string = f"Download {os.path.basename(target)}"
        download.append(link)
        holder.append(download)

    return str(soup)


# --------------------------------------------------------------------------- #
# templating
# --------------------------------------------------------------------------- #

def make_environment():
    env = Environment(loader=FileSystemLoader(ROOT))
    env.globals.update(
        first_letter_uppercase=catmus.first_letter_uppercase,
        get_last_commit=catmus.get_last_commit,
        last_update=catmus.last_update,
    )
    return env


def write(relative_path, html):
    destination = os.path.join(OUT, relative_path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(html)
    return destination


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def copy_static():
    for source_rel, dest_rel in STATIC_TREES:
        source = os.path.join(ROOT, source_rel)
        if not os.path.isdir(source):
            print(f"  ! static tree missing, skipped: {source_rel}", file=sys.stderr)
            continue
        shutil.copytree(source, os.path.join(OUT, dest_rel), dirs_exist_ok=True)


def build(with_pdf=True, with_index=True):
    started = time.time()

    pages, root_pages, sections, lang = catmus.load_manifest()
    meta = catmus.load_meta()
    env = make_environment()
    template = env.get_template("templates/index-template.html")

    # --no-pdf (which --watch implies) would otherwise drop a PDF built by an
    # earlier run, since the output tree is wiped. Keeping it means the download
    # links stay live through a watch session without paying for a rebuild.
    kept_pdf = None
    if not with_pdf and os.path.isfile(PDF_PATH):
        kept_pdf = os.path.join(tempfile.gettempdir(), "catmus-guidelines-kept.pdf")
        shutil.copy2(PDF_PATH, kept_pdf)

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    copy_static()

    # Built before the pages, so the sidebar and footer can advertise the PDF
    # only when it actually exists. Promising the link up front meant a failed
    # pandoc left every page pointing at a 404.
    pdf_built = False
    if with_pdf:
        try:
            pdf.build_pdf(catmus.pdf_pages(pages), meta, OUT)
            pdf_built = True
        except pdf.PdfUnavailable as exc:
            # A missing pandoc or xelatex must not fail the whole site build.
            print(f"  ! PDF skipped: {exc}", file=sys.stderr)
    elif kept_pdf:
        shutil.copy2(kept_pdf, PDF_PATH)
        pdf_built = True

    # Shared template context. abspath is now always "" and every asset URL is
    # root-absolute, which removes the old local-vs-production split entirely.
    common = {
        "abspath": "",
        "lang": lang,
        "meta": meta,
        "root_pages": root_pages,
        "sections": sections,
        "repository": meta.get(
            "repository",
            "https://github.com/catmus-guidelines/catmus-guidelines.github.io",
        ),
        "has_pdf": pdf_built,
        "pdf_url": "/" + PDF_NAME,
    }

    for page in pages:
        content = render_markdown(page.source_path)
        content = render_keyboard_tables(content)
        content = rewrite_internal_links(content, pages)
        html = template.render(
            **common,
            title=page.title,
            target="pages",
            current_slug=page.slug,
            content=content,
        )
        write(page.out_path, html)
        print(f"  {page.out_path}")

    # 404 and the search results shell.
    write(
        "404.html",
        env.get_template("templates/404-template.html").render(
            **common, title="Page not found", target="pages", current_slug=None
        ),
    )
    write(
        "search.html",
        template.render(
            **common,
            title="Search results",
            target="pages",
            current_slug=None,
            content="",
        ),
    )

    character_count = characters.build_character_pages(env, common, write)

    if with_index:
        index_site.build_index(OUT, pages)

    broken = check_links()

    print(
        f"built {len(pages)} pages"
        + (f" + {character_count} character pages" if character_count else "")
        + f" into {os.path.relpath(OUT, ROOT)}/ in {time.time() - started:.1f}s"
    )
    return broken


def check_links():
    """Report every local href/src in the output that does not resolve.

    Worth doing on every build: the images in this project are referenced by paths
    relative to the markdown source, and the accented filenames have already
    drifted between NFC and NFD once. A silent 404 on a manuscript example is
    exactly the kind of rot nobody notices until a reader complains.
    """
    from urllib.parse import unquote, urlparse

    broken = {}
    for directory, _, files in os.walk(OUT):
        for name in files:
            if not name.endswith(".html"):
                continue
            page = os.path.join(directory, name)
            with open(page, encoding="utf-8") as handle:
                soup = BeautifulSoup(handle.read(), "html.parser")

            for tag, attribute in (("img", "src"), ("link", "href"), ("script", "src"), ("a", "href")):
                for node in soup.find_all(tag):
                    value = node.get(attribute)
                    if not value:
                        continue
                    parsed = urlparse(value)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    path = unquote(parsed.path)
                    if path.startswith("/"):
                        target = os.path.join(OUT, path.lstrip("/"))
                    else:
                        target = os.path.normpath(os.path.join(directory, path))
                    if not os.path.exists(target):
                        broken.setdefault(value, os.path.relpath(page, OUT))

    for value, example in sorted(broken.items())[:25]:
        print(f"  ! broken link: {value}  (e.g. {example})")
    if len(broken) > 25:
        print(f"  ! ... and {len(broken) - 25} more")
    if broken:
        print(f"  ! {len(broken)} distinct broken links")
    return broken


# --------------------------------------------------------------------------- #
# serve / watch
# --------------------------------------------------------------------------- #

WATCH_PATHS = ["data", "templates", "assets", "keyboards", "scripts"]


def snapshot():
    """mtime fingerprint of every watched input. Poll-based on purpose: no
    third-party watcher dependency for a script that must run in CI."""
    state = {}
    for relative in WATCH_PATHS:
        base = os.path.join(ROOT, relative)
        for directory, _, files in os.walk(base):
            if "__pycache__" in directory:
                continue
            for name in files:
                path = os.path.join(directory, name)
                try:
                    state[path] = os.stat(path).st_mtime
                except OSError:
                    pass
    return state


def serve(port, watch, with_pdf):
    handler = functools.partial(_QuietHandler, directory=OUT)
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", port), handler)

    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\nserving {os.path.relpath(OUT, ROOT)}/ at http://localhost:{port}/")
    if watch:
        print("watching for changes; Ctrl-C to stop\n")

    try:
        if not watch:
            while True:
                time.sleep(3600)
        state = snapshot()
        while True:
            time.sleep(1)
            current = snapshot()
            if current != state:
                changed = [
                    os.path.relpath(p, ROOT)
                    for p in set(current) | set(state)
                    if current.get(p) != state.get(p)
                ]
                print(f"\nchanged: {', '.join(sorted(changed)[:4])}")
                try:
                    # PDF is skipped on rebuilds: it dominates build time and is
                    # rarely what you are iterating on.
                    build(with_pdf=False, with_index=True)
                except Exception as exc:
                    print(f"  ! build failed: {exc}", file=sys.stderr)
                state = snapshot()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.shutdown()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith(("4", "5")):
            super().log_message(fmt, *args)

    def end_headers(self):
        # Never let the preview serve a stale page from cache.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="serve _site/ after building")
    parser.add_argument("--watch", action="store_true", help="rebuild when sources change")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-pdf", action="store_true", help="skip the PDF build")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any link is broken (use in CI)",
    )
    args = parser.parse_args()

    try:
        broken = build(with_pdf=not args.no_pdf)
    except catmus.BuildError as exc:
        print(f"\nbuild error: {exc}", file=sys.stderr)
        return 1

    if args.strict and broken:
        print(f"\nbuild error: {len(broken)} broken links (--strict)", file=sys.stderr)
        return 1

    if args.serve:
        serve(args.port, args.watch, not args.no_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
