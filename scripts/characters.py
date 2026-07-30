"""The character database, parsed out of the guidelines themselves.

The authoritative list of characters is the hand-authored table in
data/guidelines/en/8_character_table.md. Rather than duplicating it into YAML,
this module reads that table and treats it as the database:

    breadth  <- table#character_table  (every character, 7 columns)
    depth    <- data/characters/*/*.md (a few characters, much richer YAML:
                                        prose description, position grid,
                                        other names, structured allographs)

Records are merged on Unicode codepoint, so a character described in both places
gets the table's coverage plus the markdown file's detail. Nothing has to be kept
in sync by hand, and the character table page keeps rendering from the same source
the authors edit.
"""

import glob
import os
import re

import yaml
from bs4 import BeautifulSoup
from marko import Markdown

import catmus

TABLE_ID = "character_table"
TABLE_SOURCE = os.path.join(catmus.GUIDELINES, "en", "8_character_table.md")
CHARACTER_MD = os.path.join(catmus.DATA, "characters", "*", "*.md")

COLUMNS = ["group", "char", "code", "name", "label", "examples", "corresp"]

# The table's Class column has drifted into near-duplicates. Without this the
# sidebar would show ten groups where there are seven.
CLASS_ALIASES = {
    "abbreviation": "Abbreviations",
    "abbreviations": "Abbreviations",
    "abbreviation (strikes)": "Abbreviations (strikes)",
    "combined abbreviation": "Combining abbreviations",
    "combining abbreviation": "Combining abbreviations",
    "superscript abbreviation": "Superscript abbreviations",
    "ligature": "Ligatures",
    "punctuation": "Punctuation",
    "reference mark": "Reference marks",
    "symbols": "Symbols",
}


class Character:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return f"<Character {self.slug} {self.char!r}>"


def normalise_class(raw):
    return CLASS_ALIASES.get(raw.strip().lower(), raw.strip() or "Other")


def codepoints(raw):
    """Extract comparable codepoints from a Unicode cell.

    Cells are not all plain `U+XXXX`: the table legitimately contains `-` for
    characters with no single codepoint, and compound descriptions such as
    `LETTER + U+0303 & LETTER + U+0303`. Returns every codepoint found, so a
    compound cell can still be matched, and an empty tuple for `-`.
    """
    return tuple(int(m, 16) for m in re.findall(r"U\+([0-9A-Fa-f]{4,6})", raw or ""))


def _text(cell):
    return cell.get_text(" ", strip=True)


def _images(cell):
    return [_example_url(img["src"]) for img in cell.find_all("img") if img.get("src")]


def _example_url(src):
    """Rewrite a table image reference to a URL the character pages can use.

    In the table the paths are relative to data/guidelines/en/ (`../../examples/x.png`),
    which is correct for the guideline pages but not for the character pages, which
    are emitted to a different depth. Root-absolute URLs work from both.
    """
    src = str(src).strip().lstrip("/")
    if src.startswith(("http://", "https://")):
        return src
    if "examples/" in src:
        return "/html/examples/" + src.split("examples/", 1)[1]
    if "img/" in src:
        return "/html/guidelines/img/" + src.split("img/", 1)[1]
    return "/" + src


def _allographs(cell):
    """Allographs are authored as bare <kbd> glyphs, with no name or code."""
    kbds = [k.get_text(strip=True) for k in cell.find_all("kbd")]
    if kbds:
        return [k for k in kbds if k]
    loose = _text(cell)
    return [loose] if loose else []


def parse_table(path=TABLE_SOURCE):
    """Parse the character table into a list of raw dicts, warning on anomalies."""
    with open(path, encoding="utf-8") as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")

    table = soup.find("table", id=TABLE_ID)
    if table is None:
        raise catmus.BuildError(f"no <table id='{TABLE_ID}'> found in {path}")

    body = table.find("tbody") or table
    records, warnings = [], []

    for position, row in enumerate(body.find_all("tr")):
        cells = row.find_all("td")
        if not cells:
            continue
        if len(cells) != len(COLUMNS):
            # Tolerated rather than fatal: a missing cell shifts later columns,
            # so report it loudly and pad so the rest of the table still builds.
            warnings.append(
                f"row {position} has {len(cells)} cells, expected {len(COLUMNS)} "
                f"({_text(cells[3]) if len(cells) > 3 else _text(cells[0])!r})"
            )
            cells = cells + [BeautifulSoup("<td></td>", "html.parser").td] * (
                len(COLUMNS) - len(cells)
            )

        raw_code = _text(cells[2])
        records.append(
            {
                "group": normalise_class(_text(cells[0])),
                "raw_group": _text(cells[0]),
                "char": _text(cells[1]),
                "code": raw_code,
                "codepoints": codepoints(raw_code),
                "name": _text(cells[3]),
                "label": _text(cells[4]),
                "examples": _images(cells[5]),
                "corresp": _allographs(cells[6]),
                "row": position,
            }
        )

    for warning in warnings:
        print(f"  ! character table: {warning}")

    return records


def load_markdown_details():
    """Read data/characters/*/*.md, keyed by codepoint for merging."""
    markdown = Markdown(extensions=["footnote"])
    by_codepoint, extra = {}, []

    for path in sorted(glob.glob(CHARACTER_MD)):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()

        parts = text.split("---")
        if len(parts) < 3:
            print(f"  ! {os.path.relpath(path, catmus.ROOT)}: no YAML front matter, skipped")
            continue

        try:
            data = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as exc:
            print(f"  ! {os.path.relpath(path, catmus.ROOT)}: bad YAML ({exc}), skipped")
            continue

        data["description_html"] = markdown.convert("---".join(parts[2:]).strip())
        data["source_md"] = os.path.relpath(path, catmus.ROOT)

        # These files reference examples as data/examples/..., which is a source
        # path rather than a URL. Rewrite both the character's own examples and
        # those nested under each related character.
        data["examples"] = [_example_url(e) for e in data.get("examples") or []]
        for related in data.get("corresp") or []:
            if isinstance(related, dict) and related.get("examples"):
                related["examples"] = [_example_url(e) for e in related["examples"]]

        # Codes in these files are zero-padded hex without the U+ prefix.
        code = str(data.get("code", "")).strip()
        try:
            key = int(code, 16)
        except (TypeError, ValueError):
            key = None

        if key is not None:
            by_codepoint[key] = data
        else:
            extra.append(data)

    return by_codepoint, extra


def load_characters():
    """The merged character list, with unique slugs, sorted for display."""
    records = parse_table()
    details, _ = load_markdown_details()

    characters, used_slugs = [], {}
    for record in records:
        merged = dict(record)

        # Merge the richer markdown record where one exists for this codepoint.
        for point in record["codepoints"]:
            if point in details:
                detail = details[point]
                for key, value in detail.items():
                    # The table wins on the fields it owns; the markdown supplies
                    # everything the table has no column for.
                    if key in ("group", "char", "code", "examples"):
                        continue
                    if value not in (None, "", []):
                        merged[key] = value
                # Prefer the table's examples; fall back to the markdown file's.
                merged["examples"] = record["examples"] or detail.get("examples", [])
                break

        merged["slug"] = _unique_slug(merged, used_slugs)
        characters.append(Character(**merged))

    characters.sort(key=lambda c: (c.group.lower(), (c.name or c.char or "").lower()))
    return characters


def _unique_slug(record, used):
    """Readable, stable, unique slug.

    Neither the name nor the code is unique in the data (two rows have no name,
    COLON appears twice, and `-` is used as a code), so fall back through name ->
    codepoint -> transliterated glyph, then disambiguate with a counter.
    """
    base = catmus.slugify(record.get("name") or "", fallback="")
    if not base and record["codepoints"]:
        base = "u" + "-".join(f"{p:04x}" for p in record["codepoints"])
    if not base:
        base = catmus.slugify(record.get("char") or "", fallback="")
    if not base:
        base = f"character-{record['row']}"

    slug = base
    if slug in used:
        used[base] += 1
        slug = f"{base}-{used[base]}"
        print(f"  ! duplicate character slug {base!r}, using {slug!r}")
    else:
        used[base] = 1
    return slug


# --------------------------------------------------------------------------- #
# page generation
# --------------------------------------------------------------------------- #

def build_character_pages(env, common, write):
    """Write one page per character plus the index. Returns the page count."""
    characters = load_characters()
    if not characters:
        return 0

    groups = {}
    for character in characters:
        groups.setdefault(character.group, []).append(character)

    template = env.get_template("templates/index-template.html")
    context = dict(common)
    context["character_groups"] = groups

    for position, character in enumerate(characters):
        previous = characters[position - 1] if position else None
        following = characters[position + 1] if position + 1 < len(characters) else None
        html = template.render(
            **context,
            title=character.name or character.label or character.char,
            target="chars",
            current_slug=None,
            character=character,
            previous_character=previous,
            next_character=following,
        )
        write(os.path.join("html", "characters", f"{character.slug}.html"), html)

    write(
        os.path.join("html", "characters", "index_of_characters.html"),
        template.render(
            **context,
            title="Index of characters",
            target="index_of_chars",
            current_slug="index_of_characters",
            characters=characters,
        ),
    )

    return len(characters)
