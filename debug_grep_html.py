"""
Grep HTML dump (saved bởi debug_html_dump.py) để extract:
- CPC: date markers thật (data-time attr, JSON-LD, time tags, span class)
- congdoandlvn: list TẤT CẢ anchor href, filter ra article links (.htm + slug ≥30 chars)
- nbtpc: dump TẤT CẢ div[id*=Content] với id thật + text length

Chạy:
    python debug_grep_html.py 2>&1 | tee /tmp/debug_grep.log
"""
from __future__ import annotations

import re
from pathlib import Path

CPC_HTML = "/tmp/cpc_article.html"
NBTPC_HTML = "/tmp/nbtpc_article.html"
CONGDOAN_HTML = "/tmp/congdoandlvn_list.html"


def section(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}", flush=True)


def grep_cpc_date() -> None:
    section("CPC — Search date markers")
    if not Path(CPC_HTML).exists():
        print(f"  {CPC_HTML} not found, skip"); return
    html = Path(CPC_HTML).read_text(errors="ignore")

    patterns = [
        ("data-time attr", r'data-time=["\']([^"\']+)["\']'),
        ("data-publish/created/date attrs", r'data-(?:publish|created|date|datetime)=["\']([^"\']+)["\']'),
        ("time tag datetime", r'<time[^>]+datetime=["\']([^"\']+)["\']'),
        ("JSON-LD datePublished", r'"datePublished"\s*:\s*"([^"]+)"'),
        ("meta article:published_time", r'<meta[^>]+article:published_time[^>]+content=["\']([^"\']+)["\']'),
        ("meta dateModified", r'<meta[^>]+(?:dateModified|date)[^>]+content=["\']([^"\']+)["\']'),
        ("Vietnamese 'Ngày đăng' phrase", r'(?:Ng[àa]y\s*đ[ăa]ng|C[aậ]p\s*nh[aậ]t|Đ[ăa]ng\s*ng[àa]y)[\s:]*([^<]{0,40})'),
        ("DD/MM/YYYY HH:MM in HTML", r'\b(\d{1,2}[/-]\d{1,2}[/-]20\d{2}\s+\d{1,2}:\d{2})\b'),
        ("DD/MM/YYYY in span/div with date class", r'class=["\'][^"\']*(?:date|time|publish|update)[^"\']*["\'][^>]*>([^<]{0,80})'),
        ("ISO 8601 date in HTML", r'\b(20\d{2}-\d{2}-\d{2}T\d{2}:\d{2})'),
    ]

    for name, pat in patterns:
        matches = re.findall(pat, html, re.I)
        # Dedupe + first 5 only
        unique = list(dict.fromkeys(matches))[:5]
        if unique:
            print(f"\n  [{name}] found {len(matches)} match(es), first 5 unique:", flush=True)
            for m in unique:
                print(f"    {m}", flush=True)
        else:
            print(f"  [{name}] NO MATCH", flush=True)


def grep_nbtpc_content_ids() -> None:
    section("nbtpc — All div[id*=Content] with text snippets")
    if not Path(NBTPC_HTML).exists():
        print(f"  {NBTPC_HTML} not found, skip"); return
    html = Path(NBTPC_HTML).read_text(errors="ignore")

    # Find all <div id="...Content..."> and approximate their content length
    div_pattern = re.compile(r'<div[^>]+id=["\']([^"\']*Content[^"\']*)["\']', re.I)
    ids = div_pattern.findall(html)
    print(f"  Found {len(ids)} div(s) with id containing 'Content':", flush=True)
    for i, did in enumerate(dict.fromkeys(ids)[:20]):
        print(f"    [{i}] id='{did}'", flush=True)


def grep_congdoan_articles() -> None:
    section("congdoandlvn — All href ending .htm with slug length")
    if not Path(CONGDOAN_HTML).exists():
        print(f"  {CONGDOAN_HTML} not found, skip"); return
    html = Path(CONGDOAN_HTML).read_text(errors="ignore")

    # Extract all href values from raw HTML
    href_pattern = re.compile(r'href=["\']([^"\']+\.htm)["\']', re.I)
    hrefs = href_pattern.findall(html)
    print(f"  Total .htm hrefs: {len(hrefs)}", flush=True)

    # Filter to slug ≥ 30 chars (likely articles)
    long_slugs = []
    for h in hrefs:
        # Strip protocol/host if absolute
        path = re.sub(r'^https?://[^/]+', '', h)
        if not path.startswith('/'):
            continue
        slug = path[1:].rstrip('.htm')
        if len(slug) >= 30:
            long_slugs.append((len(slug), path))

    long_slugs.sort(key=lambda x: -x[0])
    print(f"  hrefs with slug length ≥ 30 chars: {len(long_slugs)}", flush=True)
    print(f"  longest 20:", flush=True)
    for length, path in long_slugs[:20]:
        print(f"    [{length}] {path}", flush=True)

    # Also test current pattern
    pattern = re.compile(r'^/[a-z0-9-]{50,}\.htm$', re.I)
    matched = [p for _, p in long_slugs if pattern.search(p)]
    print(f"\n  Current pattern '^/[a-z0-9-]{{50,}}\\.htm$' matches: {len(matched)}", flush=True)
    print(f"  Sample matched (first 5):", flush=True)
    for p in matched[:5]:
        print(f"    {p}", flush=True)


if __name__ == "__main__":
    grep_cpc_date()
    grep_nbtpc_content_ids()
    grep_congdoan_articles()
