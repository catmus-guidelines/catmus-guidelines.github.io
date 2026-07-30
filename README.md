# CATMuS guidelines

Source for <https://catmus-guidelines.github.io/> — common rules for the
transcription of documents from the Middle Ages to today.

## Editing the guidelines

The pages live in `data/guidelines/en/*.md`. Every page must be listed in
**`data/guidelines/pages.yml`**, which is the single source of truth for:

* which sources are built (a missing or unlisted file fails the build);
* the URL of each page, via its `slug` — filenames can be renumbered freely
  without breaking a published link;
* the order and grouping of the sidebar;
* the chapter order of the PDF, under the separate `pdf:` key.

`data/guidelines/meta.yml` holds the PDF front matter: title, authors, and the
site URL.

A few things the build checks and warns about, because each has silently broken
a page before:

* a pipe table needs a **blank line above it**, or markdown swallows it into the
  paragraph above and it renders as rows of `|`;
* every `<span>` must be closed — an unclosed one absorbs the rest of the file;
* a table row containing a cell that reads `Transcription` is treated as a
  caption row and rendered as a sub-header.

Character descriptions live in `data/characters/{class}/{character}.md`. The
character *table* in `8_character_table.md` is the authoritative list; those
markdown files add detail to individual entries and are merged in by codepoint.

## Building

```bash
python3 -m venv venv && ./venv/bin/pip install -r scripts/requirements.txt

./venv/bin/python scripts/build.py                 # build once into _site/
./venv/bin/python scripts/build.py --serve --watch # preview on :8000, rebuild on change
./venv/bin/python scripts/build.py --no-pdf        # skip the slow PDF step
./venv/bin/python scripts/build.py --strict        # fail on any broken link (CI)
```

Output goes to `_site/`, which is gitignored — nothing generated is committed.
GitHub Actions builds and publishes that directory on every push to `gh-pages`.

### The PDF

`scripts/build.py` also renders the whole guidelines as
`_site/catmus-guidelines.pdf` via pandoc → XeLaTeX. It needs `pandoc` and
`xelatex` on PATH; without them the site still builds and the download links are
simply omitted. The PDF is the slow part of a build (~30 s), so `--watch` skips
it and reuses whatever was built last.

XeLaTeX cannot read `.woff`/`.woff2`, so `assets/fonts/` carries both the web
fonts and the `.ttf` faces that `fontspec` loads, all from the same Junicode
release, under the OFL (`assets/fonts/OFL.txt`).

## Junicode

Junicode is the point of this site's typography, not a decoration: it carries
the abbreviation marks, superscripts and combining signs the guidelines are
about (U+A751, U+0363, U+1DD3, U+204A …). It sets the body text in
`assets/css/site.css`. Note that Junicode does *not* cover U+107A5 or U+2661,
both of which the content uses — the font stack falls through to Gentium Plus /
Charis SIL / FreeSerif for those.
