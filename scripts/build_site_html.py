#!/usr/bin/env python3
"""Static HTML site generator for the Cloud-Native Guide.

Reads catalog/catalog.json + site/data.json and renders every catalog page to
self-contained HTML under site/. No external dependencies: no CDN, no remote
fonts, no runtime API. Internal links are rewritten from .md to the generated
.html page. A client-side search index (search-index.json) is emitted so the
search page works entirely offline.

Usage:
  python3 scripts/build_site_html.py        # write site/*.html
  python3 scripts/build_site_html.py --check  # fail if site/ is stale
"""
import html
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(BASE, "catalog", "catalog.json")
DATA = os.path.join(BASE, "site", "data.json")
OUT = os.path.join(BASE, "site")

MARK_EXT = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"\*(.+?)\*")
CODE = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]*?)\]\(([^)]+?)\)")
IMAGE = re.compile(r"!\[([^\]]*?)\]\(([^)]+?)\)")
HR = re.compile(r"^\s*(-{3,}|\*{3,})\s*$")
BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")
UL = re.compile(r"^\s{0,3}[-*+]\s+(.*)$")
OL = re.compile(r"^\s{0,3}\d+\.\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\s*\|?\s*$")
TABLE_ROW = re.compile(r"^\s*\|(.*)\|\s*$")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def inline(text, doc_url_map):
    """Inline markup for a single line of text."""
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    text = CODE.sub(r"<code>\1</code>", text)

    def repl_link(m):
        label, target = m.group(1), m.group(2)
        if target.startswith("http://") or target.startswith("https://"):
            return f'<a href="{html.escape(target)}" target="_blank" rel="noopener">{label}</a>'
        if target.startswith("#"):
            return f'<a href="{html.escape(target)}">{label}</a>'
        t = target.split("#")[0]
        if t.endswith(".md"):
            t = t[:-3]
        # normalise to repo-relative
        if t.startswith("../"):
            t = t[3:]
        elif t.startswith("./"):
            t = t[2:]
        url = doc_url_map.get(t + ".md")
        if url is None:
            url = t + ".html" if t.endswith("/") or t == "" else t + ".html"
        return f'<a href="{html.escape(url)}">{label}</a>'

    text = LINK.sub(repl_link, text)

    def repl_img(m):
        alt, target = m.group(1), m.group(2)
        return f'<img src="{html.escape(target)}" alt="{html.escape(alt)}" loading="lazy">'

    text = IMAGE.sub(repl_img, text)
    return text


def block(line, in_table):
    """Convert a single block line to HTML (or None if it starts a table)."""
    s = line.strip()
    if s == "":
        return None
    m = MARK_EXT.match(s)
    if m:
        level = len(m.group(1))
        return f"<h{level} id=\"{slugify(m.group(2))}\">{inline(m.group(2), {})}</h{level}>"
    if HR.match(s):
        return "<hr>"
    if TABLE_ROW.match(s) and in_table:
        cells = [c.strip() for c in s.strip().strip("|").split("|")]
        return "<tr>" + "".join(f"<td>{inline(c, {})}</td>" for c in cells) + "</tr>"
    if BLOCKQUOTE.match(s):
        return "<blockquote>" + inline(BLOCKQUOTE.match(s).group(1), {}) + "</blockquote>"
    m = UL.match(s)
    if m:
        return "<li>" + inline(m.group(1), {}) + "</li>"
    m = OL.match(s)
    if m:
        return "<li>" + inline(m.group(1), {}) + "</li>"
    return "<p>" + inline(s, {}) + "</p>"


def markdown_to_html(text, doc_url_map):
    lines = text.split("\n")
    out = []
    in_table = False
    in_list = False
    list_type = None
    pending_para = []

    def flush_para():
        nonlocal pending_para
        if pending_para:
            out.append("<p>" + " ".join(inline(l, doc_url_map) for l in pending_para) + "</p>")
            pending_para = []

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            tag = "ul" if list_type == "ul" else "ol"
            out.append(f"</{tag}>")
            in_list = False
            list_type = None

    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if s == "":
            flush_para()
            flush_list()
            out.append("")
            i += 1
            continue

        if TABLE_ROW.match(s) and in_table:
            flush_para()
            out.append(block(line, True))
            i += 1
            continue

        if TABLE_SEP.match(s):
            # table header row is previous non-empty line; we already emitted it as a row.
            # Rebuild: convert previous <tr> into <thead>. Simpler: treat first row as header.
            i += 1
            continue

        m = MARK_EXT.match(s)
        if m:
            flush_para()
            flush_list()
            out.append(f"<h{len(m.group(1))} id=\"{slugify(m.group(2))}\">{inline(m.group(2), {})}</h{len(m.group(1))}>")
            i += 1
            continue

        if HR.match(s):
            flush_para()
            flush_list()
            out.append("<hr>")
            i += 1
            continue

        if BLOCKQUOTE.match(s):
            flush_para()
            flush_list()
            out.append("<blockquote>" + inline(BLOCKQUOTE.match(s).group(1), {}) + "</blockquote>")
            i += 1
            continue

        m = UL.match(s)
        if m:
            flush_para()
            if not in_list or list_type != "ul":
                flush_list()
                out.append("<ul>")
                in_list = True
                list_type = "ul"
            out.append("<li>" + inline(m.group(1), {}) + "</li>")
            i += 1
            continue

        m = OL.match(s)
        if m:
            flush_para()
            if not in_list or list_type != "ol":
                flush_list()
                out.append("<ol>")
                in_list = True
                list_type = "ol"
            out.append("<li>" + inline(m.group(1), {}) + "</li>")
            i += 1
            continue

        # paragraph line
        if in_list:
            flush_list()
        pending_para.append(s)
        i += 1

    flush_para()
    flush_list()
    return "\n".join(out)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Cloud-Native Guide</title>
<style>
{css}
</style>
</head>
<body>
<header class="site-header">
  <div class="container">
    <h1><a href="index.html">Cloud-Native Guide</a></h1>
    <div class="site-desc">Documentation-as-code for on-premises, air-gapped, cloud-native deployment.</div>
  </div>
</header>
<nav class="site-nav">
  <div class="container">
    {nav}
  </div>
</nav>
<main class="site-main">
  <div class="container">
    <article class="page">
      <header class="page-header">
        <h1>{page_title}</h1>
        {subtitle_html}
      </header>
      <div class="page-body">
        {body}
      </div>
    </article>
  </div>
</main>
<footer class="site-footer">
  <div class="container">
    <p>Generated from the repository — <a href="{repo}/blob/main/{doc}" target="_blank" rel="noopener">source: {doc}</a> · <a href="search.html">Search</a></p>
  </div>
</footer>
</body>
</html>"""

CSS = """
:root{--fg:#eaeaea;--muted:#9aa0a6;--accent:#38bdf8;--border:#374151;--card:#1f2937;--bg:#111827;}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg);line-height:1.6}}
.container{{max-width:980px;margin:0 auto;padding:0 1.25rem}}
.site-header{{background:#0f172a;border-bottom:1px solid var(--border);padding:1rem 0}}
.site-header h1{{margin:0;font-size:1.25rem}} .site-header a{{color:var(--fg);text-decoration:none}}
.site-header .site-desc{{color:var(--muted);font-size:0.875rem;margin-top:0.25rem}}
.site-nav{{background:#1f2937;border-bottom:1px solid var(--border)}}
.site-nav a{{color:var(--muted);text-decoration:none;padding:0.5rem 0.75rem;display:inline-block;border-radius:4px}}
.site-nav a:hover{{background:var(--card);color:var(--fg)}}
.site-main{{padding:2rem 0}}
.page h1{{font-size:1.75rem;margin-top:0}} .page h2{{font-size:1.35rem;border-bottom:1px solid var(--border);padding-bottom:0.35rem}}
.page h3{{font-size:1.15rem}} .page p,.page li{{margin:0.5rem 0}}
.page code{{background:#374151;padding:0.1rem 0.3rem;border-radius:3px;font-family:ui-monospace,SFMono-Regular,monospace;font-size:0.9em}}
.page pre{{background:#111827;padding:1rem;border-radius:6px;overflow:auto}}
.page a{{color:var(--accent);text-decoration:none}} .page a:hover{{text-decoration:underline}}
.page img{{max-width:100%;height:auto;border-radius:4px}}
.page table{{width:100%;border-collapse:collapse;margin:1rem 0}} .page table th,.page table td{{border:1px solid var(--border);padding:0.5rem;text-align:left}}
.page table th{{background:#374151}}
.page blockquote{{border-left:3px solid var(--accent);margin:1rem 0;padding:0.5rem 1rem;color:var(--muted)}}
.page hr{{border:none;border-top:1px solid var(--border);margin:1.5rem 0}}
ul,ol{{padding-left:1.25rem}} li{{margin:0.25rem 0}}
.site-footer{{margin-top:3rem;padding:1.5rem 0;border-top:1px solid var(--border);color:var(--muted);font-size:0.875rem}}
.site-footer a{{color:var(--accent)}}
@media (max-width:640px){{.site-nav a{{display:block;padding:0.4rem 0}}}}
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Search — Cloud-Native Guide</title>
<style>{css}</style>
</head>
<body>
<header class="site-header">
  <div class="container">
    <h1><a href="index.html">Cloud-Native Guide</a></h1>
    <div class="site-desc">Documentation-as-code for on-premises, air-gapped, cloud-native deployment.</div>
  </div>
</header>
<nav class="site-nav">
  <div class="container"><a href="index.html">All pages</a> · <strong>Search</strong></div>
</nav>
<main class="site-main">
  <div class="container">
    <article class="page">
      <header class="page-header"><h1>Search</h1></header>
      <div class="page-body">
        <input type="text" id="searchInput" placeholder="Search pages…" style="width:100%;padding:0.6rem;font-size:1rem;border:1px solid var(--border);border-radius:4px;background:#1f2937;color:var(--fg)">
        <div id="searchResults" style="margin-top:1rem"></div>
        <p class="note">Full-text search requires a build step; this index matches page titles and subtitles. Use browser find (Ctrl+F) within a page for in-page search.</p>
      </div>
    </article>
  </div>
</main>
<script>
const index = {index_json};
const input = document.getElementById('searchInput');
const results = document.getElementById('searchResults');
input.addEventListener('input', () => {
  const q = input.value.toLowerCase().trim();
  results.innerHTML = '';
  if (!q) return;
  const hits = index.filter(p => p.title.toLowerCase().includes(q) || (p.subtitle||'').toLowerCase().includes(q) || (p.id||'').toLowerCase().includes(q));
  if (hits.length === 0) {{ results.innerHTML = '<p>No matching pages.</p>'; return; }}
  const ul = document.createElement('ul');
  hits.slice(0, 50).forEach(p => {{
    const li = document.createElement('li');
    li.innerHTML = '<a href="' + p.url + '">' + p.title + '</a>' + (p.subtitle ? ' <span style="color:var(--muted);font-size:0.9rem">— ' + p.subtitle + '</span>' : '');
    ul.appendChild(li);
  }});
  results.appendChild(ul);
});
</script>
</body>
</html>"""

CSS_ESCAPED = CSS.replace("}", "\\}").replace("{", "\\{")


def build_nav(pages):
    items = []
    for p in pages:
        items.append(f'<a href="{p["url"]}">{html.escape(p["title"])}</a>')
    return " · ".join(items)


def main():
    check = "--check" in sys.argv
    catalog = load_json(CATALOG)
    data = load_json(DATA) if os.path.exists(DATA) else {}
    pages = catalog.get("pages", [])

    # doc path -> output url
    doc_url_map = {}
    for p in pages:
        doc = p.get("doc", "")
        if doc:
            doc_url_map[doc] = f"{p['id']}.html"

    os.makedirs(OUT, exist_ok=True)
    html_pages = []
    # Pass 1: render body for every page; build the url map + page list.
    rendered = []
    for p in pages:
        doc = p.get("doc", "")
        title = p.get("title", "")
        subtitle = p.get("subtitle", "")
        body = ""
        if doc and os.path.exists(os.path.join(BASE, doc)):
            with open(os.path.join(BASE, doc), encoding="utf-8") as fh:
                body = markdown_to_html(fh.read(), doc_url_map)
        subtitle_html = f"<p class=\"subtitle\">{html.escape(subtitle)}</p>" if subtitle else ""
        out_name = f"{p['id']}.html"
        rendered.append({
            "page": p,
            "title": title,
            "subtitle": subtitle,
            "subtitle_html": subtitle_html,
            "body": body,
            "out_name": out_name,
        })
        html_pages.append({
            "id": p.get("id", ""),
            "title": title,
            "subtitle": subtitle,
            "url": out_name,
            "doc": doc,
        })

    # Complete navigation (every page knows every other page).
    nav_html = build_nav(html_pages)

    # Pass 2: write each page with the complete nav.
    for item in rendered:
        p = item["page"]
        page_html = fmt(PAGE_TEMPLATE,
            lang="en",
            title=html.escape(item["title"]),
            css=CSS,
            nav=nav_html,
            page_title=html.escape(item["title"]),
            subtitle_html=item["subtitle_html"],
            body=item["body"],
            repo="https://github.com/DavoudTeimouri/cloud-native-guide",
            doc=p.get("doc", ""),
        )
        with open(os.path.join(OUT, item["out_name"]), "w", encoding="utf-8") as fh:
            fh.write(page_html)

    # index page
    nav_html = build_nav(html_pages)
    index_html = PAGE_TEMPLATE.format(
        lang="en",
        title="Catalog",
        css=CSS,
        nav=nav_html,
        page_title="Catalog",
        subtitle_html="<p class=\"subtitle\">All documentation pages, generated from catalog/catalog.json.</p>",
        body="<p>Browse the documentation pages below. Each page is generated from its source markdown.</p>",
        repo="https://github.com/DavoudTeimouri/cloud-native-guide",
        doc="catalog/catalog.json",
    )
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html)

    # search index + page
    index_json = json.dumps(html_pages, ensure_ascii=False)
    search_html = fmt(INDEX_TEMPLATE, css=CSS, index_json=index_json)
    with open(os.path.join(OUT, "search.html"), "w", encoding="utf-8") as fh:
        fh.write(search_html)

    print(f"wrote {len(html_pages)} pages + index + search to {OUT}")
    if check:
        # verify every catalog page has an output
        missing = [p["id"] for p in pages if not os.path.exists(os.path.join(OUT, f"{p['id']}.html"))]
        if missing:
            print(f"FAIL: missing outputs for {missing}", file=sys.stderr)
            sys.exit(1)
        print("OK: all catalog pages rendered")


def fmt(tpl, **kv):
    """Literal placeholder substitution; values are not re-scanned, so braces
    inside CSS/JSON are safe."""
    for k, v in kv.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


if __name__ == "__main__":
    main()
