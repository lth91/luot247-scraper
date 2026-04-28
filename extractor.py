"""
Playwright fetch + extract: dùng headless Chromium để render JS, lấy link bài từ list page,
fetch từng bài, trích text + meta date. Crawler-style giống discovery-rss-news (Edge Function)
nhưng có browser engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from sources import Source

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

LIST_TIMEOUT_MS = 25000
ARTICLE_TIMEOUT_MS = 20000
MAX_LINKS_PER_SOURCE = 8
MIN_CONTENT_CHARS = 250
MAX_CONTENT_CHARS = 8000


@dataclass
class Article:
    source_name: str
    source_category: str
    title: str
    content: str
    url: str
    url_hash: str
    published_at: str | None  # ISO 8601 hoặc None


def canonicalize(raw: str, base: str) -> str | None:
    try:
        u = urlparse(urljoin(base, raw))
        scheme = u.scheme or "https"
        netloc = u.netloc.lower()
        path = u.path.rstrip("/") or "/"
        # Bỏ utm_*, fbclid khỏi query
        from urllib.parse import parse_qsl, urlencode

        keep = [(k, v) for k, v in parse_qsl(u.query) if not k.startswith("utm_") and k not in {"fbclid", "gclid"}]
        q = urlencode(keep)
        s = f"{scheme}://{netloc}{path}"
        if q:
            s += f"?{q}"
        return s
    except Exception:
        return None


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


META_DATE_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']article:published_time["\']', re.I),
    re.compile(r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"'),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.I),
]

# Inline DD/MM/YYYY format hay xuất hiện trong HTML của EVN family
INLINE_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")


def extract_published_from_html(html: str) -> str | None:
    from datetime import datetime, timezone

    for pat in META_DATE_PATTERNS:
        m = pat.search(html)
        if m:
            try:
                # Heuristic: parse ISO; nếu fail, bỏ qua
                raw = m.group(1).strip()
                # Một số site dùng "+0710:14:17" ngộ nghĩnh — strip suffix nếu có lỗi parse
                try:
                    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    # Try split ngoài timezone
                    base = raw.split("+")[0].split("Z")[0]
                    dt = datetime.fromisoformat(base)
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                continue
    # Fallback: inline DD/MM/YYYY trong 3000 ký tự đầu của body
    m = INLINE_DATE_RE.search(html[:3000])
    if m:
        d, mo, y = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if 2020 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(y, mo, d, tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    return None


async def extract_links(page: Page, source: Source) -> list[str]:
    """Lấy danh sách link bài từ list page, dedupe, match link_pattern."""
    try:
        await page.goto(source.list_url, wait_until="domcontentloaded", timeout=LIST_TIMEOUT_MS)
        if source.wait_for:
            try:
                await page.wait_for_selector(source.wait_for, timeout=8000)
            except Exception:
                pass  # Selector không xuất hiện → vẫn thử extract
        # Thêm 1.5s cho lazy-load các <a> chậm
        await asyncio.sleep(1.5)
    except Exception as e:
        print(f"  [{source.name}] list page load error: {e}", flush=True)
        return []

    hrefs = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(a => a.getAttribute('href'))",
    )
    pattern = re.compile(source.link_pattern, re.I)
    seen: set[str] = set()
    out: list[str] = []
    base_origin = f"{urlparse(source.list_url).scheme}://{urlparse(source.list_url).netloc}"
    for href in hrefs:
        if not href:
            continue
        canon = canonicalize(href, source.list_url)
        if not canon:
            continue
        # Same-host only
        if urlparse(canon).netloc.lower() != urlparse(base_origin).netloc.lower():
            continue
        # Match pattern trên pathname (hoặc full URL — pattern viết để match được cả 2)
        path = urlparse(canon).path
        if not pattern.search(path):
            continue
        if canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
        if len(out) >= MAX_LINKS_PER_SOURCE:
            break
    return out


async def fetch_article(context: BrowserContext, source: Source, url: str) -> Article | None:
    page = await context.new_page()
    try:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=ARTICLE_TIMEOUT_MS)
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"  [{source.name}] article goto error {url}: {e}", flush=True)
            return None

        # Lấy raw HTML cho meta-date extraction
        html = await page.content()

        # Title: og:title → <title> → h1
        title = await page.evaluate(
            """() => {
              const og = document.querySelector("meta[property='og:title']");
              if (og) return og.getAttribute("content");
              const t = document.querySelector("title");
              if (t) return t.textContent;
              const h1 = document.querySelector("h1");
              return h1 ? h1.textContent : "";
            }"""
        )
        title = (title or "").strip()

        # Content extraction: thử content_selector; fallback main/article; fallback p concat
        selectors = []
        if source.content_selector:
            selectors.extend([s.strip() for s in source.content_selector.split(",")])
        selectors.extend(["main article", "article", "main", "div.content"])

        content = ""
        for sel in selectors:
            try:
                txt = await page.evaluate(
                    """(sel) => {
                      const els = document.querySelectorAll(sel);
                      let best = "";
                      els.forEach(el => {
                        const t = (el.innerText || "").trim();
                        if (t.length > best.length) best = t;
                      });
                      return best;
                    }""",
                    sel,
                )
                if txt and len(txt) > MIN_CONTENT_CHARS:
                    content = txt
                    break
            except Exception:
                continue

        # Fallback cuối: concat <p>
        if len(content) < MIN_CONTENT_CHARS:
            content = await page.evaluate(
                """() => {
                  const ps = document.querySelectorAll("main p, article p, body p");
                  return Array.from(ps).map(p => (p.innerText || "").trim()).filter(t => t.length > 40).join("\\n");
                }"""
            )

        content = re.sub(r"\s+", " ", content or "").strip()[:MAX_CONTENT_CHARS]
        if len(content) < MIN_CONTENT_CHARS:
            print(f"  [{source.name}] content too short ({len(content)}): {url}", flush=True)
            return None

        published_at = extract_published_from_html(html)
        return Article(
            source_name=f"Mac Mini ({source.name})",
            source_category=source.category,
            title=title or "(không có tiêu đề)",
            content=content,
            url=url,
            url_hash=sha256_hex(url),
            published_at=published_at,
        )
    finally:
        await page.close()


async def crawl_source(browser: Browser, source: Source) -> list[Article]:
    """Crawl 1 nguồn: load list page → extract links → fetch từng bài."""
    context = await browser.new_context(user_agent=UA, locale="vi-VN")
    list_page = await context.new_page()
    articles: list[Article] = []
    try:
        links = await extract_links(list_page, source)
        await list_page.close()
        print(f"  [{source.name}] {len(links)} link(s) match pattern", flush=True)
        for url in links:
            art = await fetch_article(context, source, url)
            if art:
                articles.append(art)
    finally:
        await context.close()
    return articles


async def crawl_all(sources: list[Source]) -> list[Article]:
    """Boot 1 browser, crawl tuần tự từng nguồn (tránh nuốt RAM)."""
    out: list[Article] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for source in sources:
                print(f"[crawl] {source.name}", flush=True)
                try:
                    arts = await crawl_source(browser, source)
                    out.extend(arts)
                except Exception as e:
                    print(f"  [{source.name}] FATAL: {e}", flush=True)
        finally:
            await browser.close()
    return out
