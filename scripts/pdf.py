"""Render the whole guidelines as one PDF: markdown -> pandoc -> XeLaTeX.

Why a preprocessing pass exists
-------------------------------
The guideline sources are markdown with a lot of raw HTML embedded in them: two
full <table>s (the 51-row character table and the datasets table), 106 <img>, 36
<span class="rule">, plus <kbd>, <br>, <sup> and <a>. **Pandoc discards raw HTML
when the target is LaTeX**, so handing these files to pandoc unmodified would
silently drop the character table -- the single most valuable part of the
document -- and every rule highlight.

So `normalise()` rewrites the HTML constructs the project actually uses into
pandoc-native markdown (or raw-LaTeX blocks) first. Anything it does not
recognise is reported, so a new construct fails loudly instead of vanishing.

XeLaTeX is used rather than pdfLaTeX because the document is full of medieval
codepoints (U+A751, U+0363, U+1DD3 ...) that only Junicode covers, and fontspec
can load Junicode directly.
"""

import os
import re
import shutil
import subprocess
import tempfile

from bs4 import BeautifulSoup, NavigableString

import catmus
import characters as characters_module

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "guidelines.tex")

# Junicode must be a real font file on disk for fontspec: XeLaTeX cannot read
# .woff/.woff2, which is all the repository ships for the web. Preference order
# favours a vendored OTF/TTF, then a system install.
JUNICODE_DIRS = [
    os.path.join(catmus.ROOT, "assets", "fonts"),
    "/usr/share/fonts/truetype/junicode",
    "/usr/share/fonts/opentype/junicode",
]

# fontspec is told each face explicitly rather than left to guess from a family
# name, so the build uses the vendored files and never a differing system copy.
JUNICODE_FACES = {
    "upright": "Junicode-Regular.ttf",
    "bold": "Junicode-Bold.ttf",
    "italic": "Junicode-Italic.ttf",
    "bolditalic": "Junicode-BoldItalic.ttf",
}


class PdfUnavailable(Exception):
    """The PDF could not be built. Never fatal to the site build."""


# --------------------------------------------------------------------------- #
# HTML -> pandoc-native
# --------------------------------------------------------------------------- #

def _latex_escape(text):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _resolve_image(src, source_dir):
    """Turn a source-relative image reference into an absolute path.

    Content uses paths relative to the markdown file (../img/x.png,
    ../../examples/y.png), which is what the website relies on too.
    """
    if src.startswith(("http://", "https://")):
        return None
    path = os.path.normpath(os.path.join(source_dir, src.lstrip("/")))
    return path if os.path.isfile(path) else None


# The character table's columns hold very different amounts of text -- a one-glyph
# Character column next to a full Unicode name -- so equal widths waste most of
# the page. Keyed by column count; anything else falls back to equal widths.
COLUMN_WEIGHTS = {
    7: [0.13, 0.07, 0.11, 0.24, 0.19, 0.16, 0.10],
}


def _table_to_latex(table, source_dir, warnings, landscape=False, glyph_columns=()):
    """Render an HTML table as a LaTeX longtable.

    Images inside cells become \\includegraphics boxes; glyph cells are wrapped in
    the Junicode font command so medieval characters survive.
    """
    rows = []
    header = []

    head = table.find("thead")
    if head:
        header = [_cell_to_latex(c, source_dir, warnings) for c in head.find_all(["th", "td"])]

    body = table.find("tbody") or table
    for row in body.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        rows.append(
            [
                _cell_to_latex(c, source_dir, warnings, glyph=index in glyph_columns)
                for index, c in enumerate(cells)
            ]
        )

    if not rows:
        return ""

    width = max([len(header)] + [len(r) for r in rows])
    header += [""] * (width - len(header))
    rows = [r + [""] * (width - len(r)) for r in rows]

    # Fixed-width p{} columns: these tables have long labels and stacked images,
    # and are the only thing that wraps sanely.
    #
    # The widths must be shares of the text block *minus* the inter-column
    # padding, which is 2\tabcolsep per column. Taking them as plain fractions of
    # \linewidth makes the table wider than the page by that padding -- 43pt for
    # the seven-column character table -- and the overflow lands on the last
    # columns, pushing the example images out past the table rule.
    weights = COLUMN_WEIGHTS.get(width) or [1.0 / width] * width
    total = sum(weights)
    padding = 2 * width
    spec = " ".join(
        ">{\\raggedright\\arraybackslash}"
        f"p{{(\\linewidth - {padding}\\tabcolsep) * \\real{{{w / total:.4f}}}}}"
        for w in weights
    )

    lines = [r"\begingroup\footnotesize", rf"\begin{{longtable}}{{{spec}}}", r"\hline"]
    if any(header):
        lines.append(" & ".join(rf"\textbf{{{h}}}" for h in header) + r" \\")
        lines.append(r"\hline\endhead")
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\hline", r"\end{longtable}", r"\endgroup"]

    latex = "\n".join(lines)
    if landscape:
        latex = "\\begin{landscape}\n" + latex + "\n\\end{landscape}"
    return latex


def _cell_to_latex(cell, source_dir, warnings, glyph=False):
    """Serialise one table cell to LaTeX inline content.

    `glyph` marks a column whose whole content is a character being documented
    (the character table's "Character(s)"), which needs the enlarged treatment
    that <kbd> gets elsewhere -- at body size the combining marks are unreadable.
    """
    parts = []
    for node in cell.descendants:
        if isinstance(node, NavigableString):
            if node.parent.name in ("kbd", "img"):
                continue
            text = str(node).strip()
            if text:
                escaped = _latex_escape(text)
                parts.append(rf"\glyph{{{escaped}}}" if glyph else escaped)
        elif node.name == "img":
            path = _resolve_image(node.get("src", ""), source_dir)
            if path:
                parts.append(rf"\exampleimage{{{path}}}")
            else:
                warnings.append(f"image not found: {node.get('src')}")
        elif node.name == "br":
            # Line breaks inside a cell are meaningful -- these are line-by-line
            # transcriptions of a manuscript. \newline works in a p{} column.
            parts.append(r"\newline{}")
        elif node.name == "kbd":
            glyph = node.get_text(strip=True)
            if glyph:
                parts.append(rf"\glyph{{{_latex_escape(glyph)}}}")
    return " ".join(parts)


def _protect_code_spans(text):
    """Hide inline code spans from the HTML parser.

    The prose deliberately quotes pseudo-elements like `` `<tilde>` `` and
    `` `<macron>` ``. BeautifulSoup reads those as unknown tags and swallows
    them, exactly as the website did before they were escaped. Stash each span
    behind a placeholder and restore it after the HTML rewriting is done.
    """
    stash = []

    def keep(match):
        stash.append(match.group(0))
        return f"\x00CODE{len(stash) - 1}\x00"

    return re.sub(r"`[^`\n]+`", keep, text), stash


def _restore_code_spans(text, stash):
    for position, original in enumerate(stash):
        text = text.replace(f"\x00CODE{position}\x00", original)
    return text


def _rewrite_markdown_images(text, source_dir, warnings):
    """Resolve `![alt](../img/x.png)` to an absolute path and give it a width.

    Two things are being fixed here.

    The path: pandoc resolves images against --resource-path, but these are
    written relative to the markdown file itself, so one shared resource path
    cannot serve pages at different depths. Resolving here makes every
    reference unambiguous.

    The width: `{width=100%}` becomes `\\includegraphics[width=\\linewidth]`,
    which inside a table cell is the column width. Without it the rendering
    depends on the pandoc version -- 3.5 and later wrap images in
    \\pandocbounded, which scales them to fit, while older releases (3.1.3, the
    one Ubuntu ships and CI therefore used) emit the image at its natural size.
    These scans are far wider than any column, so on the older pandoc they ran
    straight through the cell and off the page, and the document came out five
    pages longer. Stating the width keeps both versions identical.
    """

    def replace(match):
        alt, src = match.group(1), match.group(2).strip()
        if src.startswith(("http://", "https://")):
            return match.group(0)
        path = _resolve_image(src, source_dir)
        if path is None:
            warnings.append(f"image not found: {src}")
            return ""
        return f"![{alt}]({path}){{width=100%}}"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, text)


DELIMITER_ROW = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|[\s:|-]*$")

# Placeholder standing in for <br> until we know whether it fell inside a table.
BREAK = "\x00BR\x00"


def _resolve_breaks(text):
    """Turn the <br> placeholders into whatever works where they landed.

    The transcriptions are line-by-line renderings of a manuscript, so the line
    breaks carry meaning and cannot be dropped. But a markdown hard break is a
    real newline, and a newline inside a pipe-table row *ends the row* -- which
    is why the multi-line transcriptions were coming out as one run-on line.
    Inside a table the break has to be raw LaTeX instead; \\newline is valid in
    the p{} columns pandoc generates for pipe tables.
    """
    lines = []
    for line in text.split("\n"):
        if BREAK not in line:
            lines.append(line)
            continue
        if line.lstrip().startswith("|"):
            lines.append(line.replace(BREAK, "`\\newline{}`{=latex}"))
        else:
            lines.append(line.replace(BREAK, "  \n"))
    return "\n".join(lines)


def _split_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _normalise_pipe_tables(text):
    """Fix the column widths, caption rows and text size of the pipe tables.

    Pandoc sizes a pipe table's columns in proportion to the dashes under each
    heading. The sources were written for a web renderer that ignores them, so
    they are wildly uneven -- `|--------|-------...80 dashes...|` gives the first
    column 9% of the page, and since that column is usually the manuscript image
    it collapses to an illegible smudge.

    Returns the rewritten lines plus the (first, last) extent of every table
    that carries a "Transcription" column, for the caller to wrap in \\small.
    """
    lines = text.split("\n")
    tables_to_wrap = []
    for number, line in enumerate(lines):
        if "-" not in line or "|" not in line or not DELIMITER_ROW.match(line):
            continue

        cells = _split_row(line)

        # Equal columns. The recurring shape is "manuscript image |
        # transcription", where the scan scales to whatever it is given and the
        # reading beside it needs room; anything other than 50/50 starves one of
        # the two.
        rebuilt = []
        for cell in cells:
            left = ":" if cell.startswith(":") else ""
            right = ":" if cell.endswith(":") else ""
            rebuilt.append(f"{left}{'-' * 12}{right}")
        lines[number] = "|" + "|".join(rebuilt) + "|"

        # The extent of this table: the header line above, the body below.
        first = number - 1
        last = number
        for following in lines[number + 1:]:
            if not following.lstrip().startswith("|"):
                break
            last += 1

        rows = [_split_row(lines[i]) for i in [first] + list(range(number + 1, last + 1))]
        if not any(_is_caption_row(row) for row in rows):
            continue

        # A row that says "Transcription" partway down the body is a caption for
        # the example beneath it, not data. Markdown has no second header row,
        # so it is emphasised instead.
        for i in range(number + 1, last + 1):
            row = _split_row(lines[i])
            if _is_caption_row(row):
                lines[i] = "|" + "|".join(f" **{c}** " if c else " " for c in row) + "|"

        # Small text for the whole table, matching the website.
        tables_to_wrap.append((first, last))

    return lines, tables_to_wrap


def _is_caption_row(cells):
    return any(cell.strip().lower() == "transcription" for cell in cells)


def _shrink_transcription_tables(text):
    """Set the example/transcription tables in \\small, as the website does.

    Wrapping happens after the rewrite pass so the recorded line numbers are
    still valid; the insertions are applied from the bottom up for the same
    reason.
    """
    lines, extents = _normalise_pipe_tables(text)
    for first, last in sorted(extents, reverse=True):
        lines.insert(last + 1, "\n```{=latex}\n\\endgroup\n```\n")
        lines.insert(first, "\n```{=latex}\n\\begingroup\\small\n```\n")
    return "\n".join(lines)


def normalise(text, source_dir, warnings):
    """Rewrite the embedded HTML this project uses into pandoc-native markdown."""
    text, code_spans = _protect_code_spans(text)
    soup = BeautifulSoup(text, "html.parser")

    # Keyboard placeholders: same data the website renders, as a LaTeX table.
    for holder in soup.select("div.json"):
        target = holder.get("data-target", "")
        path = os.path.join(catmus.ROOT, target)
        replacement = ""
        if os.path.isfile(path):
            import json

            with open(path, encoding="utf-8") as handle:
                keyboard = json.load(handle)
            replacement = _keyboard_to_latex(keyboard)
        else:
            warnings.append(f"keyboard JSON not found: {target}")
        holder.replace_with(_raw_latex_block(soup, replacement))

    # Tables -> longtable. The character table is seven columns wide, so it goes
    # landscape; anything narrower stays portrait.
    for table in soup.find_all("table"):
        is_characters = table.get("id") == "character_table"
        landscape = is_characters or len(table.find_all("th")) >= 6
        latex = _table_to_latex(
            table,
            source_dir,
            warnings,
            landscape=landscape,
            glyph_columns=(1,) if is_characters else (),
        )
        table.replace_with(_raw_latex_block(soup, latex))

    # Standalone images -> markdown images with resolved paths.
    for img in soup.find_all("img"):
        path = _resolve_image(img.get("src", ""), source_dir)
        alt = (img.get("alt") or "").replace("]", "")
        if path:
            img.replace_with(NavigableString(f"![{alt}]({path})"))
        else:
            warnings.append(f"image not found: {img.get('src')}")
            img.replace_with(NavigableString(""))

    for kbd in soup.find_all("kbd"):
        kbd.replace_with(NavigableString(f"`{kbd.get_text(strip=True)}`"))

    for sup in soup.find_all("sup"):
        sup.replace_with(NavigableString(f"^{sup.get_text(strip=True)}^"))

    # <br> means two different things depending on where it lands, and the
    # difference cannot be decided until the markdown has been serialised, so
    # stash a sentinel and resolve it in _resolve_breaks().
    for br in soup.find_all("br"):
        br.replace_with(NavigableString(BREAK))

    for anchor in soup.find_all("a"):
        label = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        anchor.replace_with(NavigableString(f"[{label}]({href})" if href else label))

    for div in soup.find_all("div"):
        div.unwrap()

    # formatter=None disables HTML entity escaping. The output here is markdown
    # bound for pandoc, not HTML, so the default formatter turns every literal
    # "&" in the prose (there are many: "a & b", "&" [U+0026]) into "&amp;",
    # which pandoc then prints verbatim.
    result = soup.decode(formatter=None)

    # Anything still looking like a tag is an unhandled construct: report it
    # rather than let pandoc quietly discard it. Checked before code spans are
    # restored, so prose that deliberately quotes `<tilde>` is not flagged.
    for leftover in set(re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)[\s/>]", result)):
        if leftover.lower() not in ("br",):
            warnings.append(f"unhandled HTML element <{leftover}> left in source")

    result = _restore_code_spans(result, code_spans)
    result = _resolve_breaks(result)
    result = _shrink_transcription_tables(result)
    return _rewrite_markdown_images(result, source_dir, warnings)


def _raw_latex_block(soup, latex):
    return NavigableString("\n\n```{=latex}\n" + latex + "\n```\n\n")


def _keyboard_to_latex(keyboard):
    chars = keyboard.get("characters", [])
    if not chars:
        return ""
    rows = max(c["row"] for c in chars) + 1
    cols = max(c["column"] for c in chars) + 1
    grid = [[""] * cols for _ in range(rows)]
    for char in chars:
        grid[char["row"]][char["column"]] = rf"\glyph{{{_latex_escape(char['character'])}}}"

    spec = "|" + "c|" * cols
    lines = [
        rf"\subsection*{{{_latex_escape(keyboard.get('name', 'Keyboard'))}}}",
        r"\begingroup\small",
        rf"\begin{{longtable}}{{{spec}}}",
        r"\hline",
    ]
    for row in grid:
        lines.append(" & ".join(row) + r" \\ \hline")
    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def find_junicode():
    """The directory holding a complete set of Junicode faces, or None."""
    for directory in JUNICODE_DIRS:
        if all(os.path.isfile(os.path.join(directory, f)) for f in JUNICODE_FACES.values()):
            return directory
    return None


def build_pdf(pages, meta, out_root):
    if shutil.which("pandoc") is None:
        raise PdfUnavailable("pandoc is not installed (apt-get install pandoc)")
    if shutil.which("xelatex") is None:
        raise PdfUnavailable("xelatex is not installed (apt-get install texlive-xetex)")

    junicode = find_junicode()
    if junicode is None:
        raise PdfUnavailable(
            "no complete set of Junicode .ttf faces found. XeLaTeX cannot use the "
            ".woff/.woff2 the site ships; put "
            + ", ".join(sorted(JUNICODE_FACES.values()))
            + " in assets/fonts/ (see README)"
        )

    warnings = []
    chunks = []

    for page in pages:
        with open(page.source_path, encoding="utf-8") as handle:
            body = handle.read()

        body = normalise(body, os.path.dirname(page.source_path), warnings)
        # The manifest title is the chapter heading, so nothing in the source may
        # also be level 1: 4_abbreviations.md opens with `# Abbreviations`, which
        # produced a duplicate, empty "Abbreviations" chapter in the contents.
        body = re.sub(r"^# (?=\S)", "## ", body, flags=re.MULTILINE)
        chunks.append(f"\n\n# {page.title}\n\n{body}\n")

    document = "\n".join(chunks)

    for warning in sorted(set(warnings)):
        print(f"  ! pdf: {warning}")

    authors = meta.get("authors") or []
    if meta.get("corporate_author"):
        authors = list(authors) + [meta["corporate_author"]]

    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "guidelines.md")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(document)

        destination = os.path.join(out_root, "catmus-guidelines.pdf")
        command = [
            "pandoc",
            source,
            "-o", destination,
            # Pipe tables are the only table syntax the sources use. The others
            # must be switched off: several pages separate their footnotes with a
            # `------` rule, which pandoc's simple_tables reader takes for a table
            # delimiter and silently folds the whole Notes section into a narrow
            # one-column table.
            "--from",
            "markdown+raw_attribute+footnotes+bracketed_spans+pipe_tables"
            "-simple_tables-multiline_tables-grid_tables",
            "--pdf-engine", "xelatex",
            "--toc", "--toc-depth=2",
            "--number-sections",
            "--resource-path", catmus.ROOT,
            "-V", f"junicodedir={junicode}{os.sep}",
            "-V", f"junicodeupright={JUNICODE_FACES['upright']}",
            "-V", f"junicodebold={JUNICODE_FACES['bold']}",
            "-V", f"junicodeitalic={JUNICODE_FACES['italic']}",
            "-V", f"junicodebolditalic={JUNICODE_FACES['bolditalic']}",
            "-V", f"title={meta.get('title', 'CATMuS')}",
            "-V", f"subtitle={meta.get('subtitle', '')}",
            "-V", f"siteurl={meta.get('url', '')}",
            "-V", f"licence={meta.get('license', '')}",
            "-V", f"version={meta.get('version', '')}",
            "-V", f"commit={catmus.get_last_commit()}",
            "-V", f"builddate={catmus.last_update()}",
        ]
        for author in authors:
            command += ["-V", f"author={author}"]
        if os.path.isfile(TEMPLATE):
            command += ["--template", TEMPLATE]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise PdfUnavailable(
                "pandoc/xelatex failed:\n"
                + (result.stderr or result.stdout)[-2500:]
            )

    size = os.path.getsize(destination) / 1024
    print(f"  catmus-guidelines.pdf ({size:.0f} kB)")
    return destination
