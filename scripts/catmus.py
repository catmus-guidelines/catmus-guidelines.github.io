"""Shared helpers for the CATMuS build: paths, the page manifest, and markdown.

Kept separate from build.py so that pdf.py and characters.py can reuse the
manifest without importing the whole site builder.
"""

import datetime
import os
import re
import subprocess
import unicodedata

import yaml

# Repository root, derived from this file so the build works from any cwd.
# The old script relied on being run from the repo root and broke otherwise.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(ROOT, "data")
GUIDELINES = os.path.join(DATA, "guidelines")
TEMPLATES = os.path.join(ROOT, "templates")
OUT = os.path.join(ROOT, "_site")

MANIFEST = os.path.join(GUIDELINES, "pages.yml")
META = os.path.join(GUIDELINES, "meta.yml")


class BuildError(Exception):
    """Raised for conditions that must fail the build rather than warn."""


class Page:
    """One markdown source and everything the build needs to place it."""

    def __init__(self, source, slug, title, lang, section=None, at_root=False):
        self.source = source
        self.slug = slug
        self.title = title
        self.lang = lang
        self.section = section
        self.at_root = at_root

    @property
    def source_path(self):
        return os.path.join(GUIDELINES, self.lang, self.source)

    @property
    def out_path(self):
        """Path inside _site/. Root pages sit at the top level; grouped pages keep
        the html/guidelines/<lang>/ prefix so existing published URLs still work."""
        if self.at_root:
            return f"{self.slug}.html"
        return os.path.join("html", "guidelines", self.lang, f"{self.slug}.html")

    @property
    def url(self):
        return "/" + self.out_path.replace(os.sep, "/")

    def __repr__(self):
        return f"<Page {self.slug} <- {self.source}>"


def load_meta():
    with open(META, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_manifest():
    """Read pages.yml into (pages, sections, lang).

    Fails loudly when a listed source is missing, and when a markdown file on disk
    is not listed. Silent drift between the manifest and the sources is what broke
    the build on this branch, so it is treated as an error rather than a warning.
    """
    with open(MANIFEST, encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)

    lang = manifest.get("lang", "en")
    pages = []
    root_pages = []

    for entry in manifest.get("root", []):
        page = Page(entry["source"], entry["slug"], entry["title"], lang, at_root=True)
        pages.append(page)
        root_pages.append(page)

    sections = []
    for section in manifest.get("sections", []):
        section_pages = []
        for entry in section.get("pages", []):
            page = Page(
                entry["source"],
                entry["slug"],
                entry["title"],
                lang,
                section=section.get("id", section["title"]),
            )
            pages.append(page)
            section_pages.append(page)
        sections.append(
            {
                "title": section["title"],
                "id": section.get("id", slugify(section["title"])),
                "pages": section_pages,
            }
        )

    _check_manifest_matches_disk(pages, lang)
    return pages, root_pages, sections, lang


def pdf_pages(pages):
    """The pages that go into the PDF, in the manifest's `pdf:` order.

    The PDF is a different document from the website, not a dump of it: the
    site-navigation pages have no place in something read on its own, and the
    order differs too. Falling back to every page when `pdf:` is absent keeps
    older manifests working.
    """
    with open(MANIFEST, encoding="utf-8") as handle:
        order = (yaml.safe_load(handle) or {}).get("pdf")

    if not order:
        return list(pages)

    by_slug = {page.slug: page for page in pages}
    unknown = [slug for slug in order if slug not in by_slug]
    if unknown:
        raise BuildError(
            "pages.yml `pdf:` lists slugs that are not pages: "
            f"{', '.join(unknown)}"
        )
    return [by_slug[slug] for slug in order]


def _check_manifest_matches_disk(pages, lang):
    missing = [p.source for p in pages if not os.path.isfile(p.source_path)]
    if missing:
        raise BuildError(
            "pages.yml lists sources that do not exist in "
            f"data/guidelines/{lang}/: {', '.join(sorted(missing))}"
        )

    listed = {p.source for p in pages}
    source_dir = os.path.join(GUIDELINES, lang)
    on_disk = {f for f in os.listdir(source_dir) if f.endswith(".md")}
    unlisted = on_disk - listed
    if unlisted:
        raise BuildError(
            f"markdown files in data/guidelines/{lang}/ are not listed in pages.yml, "
            f"so they would be silently dropped from the site: {', '.join(sorted(unlisted))}. "
            "Add them to pages.yml (or delete them)."
        )

    duplicate_slugs = _duplicates([p.slug for p in pages])
    if duplicate_slugs:
        raise BuildError(f"duplicate slugs in pages.yml: {', '.join(duplicate_slugs)}")


def _duplicates(values):
    seen, dupes = set(), set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return sorted(dupes)


def slugify(text, fallback="item"):
    """ASCII slug suitable for a filename, preserving readability."""
    normalised = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or fallback


def last_update():
    return datetime.datetime.today().strftime("%Y-%m-%d")


def get_last_commit():
    """Short commit hash, or a placeholder outside a git checkout.

    The old version let a git failure abort the whole build; a missing hash is not
    worth failing over.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=10", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def first_letter_uppercase(string):
    string = str(string)
    return string[:1].upper() + string[1:]
