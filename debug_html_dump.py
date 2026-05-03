"""
Dump raw HTML của 1 article URL để inspect:
- date markers (cho CPC date extraction)
- body container (cho nbtpc content selector)
- congdoandlvn list page (mystery 0-link match)

Chạy:
    source ~/.openclaw/venv-luot247/bin/activate
    python debug_html_dump.py 2>&1 | tee /tmp/debug_html.log

Output:
    - /tmp/cpc_article.html   — 1 bài CPC để eyeball date format
    - /tmp/nbtpc_article.html — 1 bài nbtpc để eyeball body container
    - /tmp/congdoandlvn_list.html — list page để xem anchor structure
"""
from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright

DUMPS = [
    {
        "name": "CPC article",
        "url": "https://cpc.vn/vi-vn/Tin-tuc-su-kien/Tin-tuc-chi-tiet/articleId/107280",
        "out": "/tmp/cpc_article.html",
        # 15s wait — CPC dùng JS render relative time ("X giờ trước"); cần đợi JS
        # finish để timePassed text được thay vào span.
        "wait_ms": 15000,
    },
    {
        "name": "nbtpc article",
        "url": "https://nbtpc.com.vn/d4/news/THONG-TIN-VE-ANH-HUONG-CUA-CON-BAO-SO-10-BUALOI-DEN-VAN-HANH-VA-CUNG-CAP-DIEN--1-5423.aspx",
        "out": "/tmp/nbtpc_article.html",
        "wait_ms": 4000,
    },
    {
        "name": "congdoandlvn list",
        "url": "https://www.congdoandlvn.org.vn/tin-tuc.htm",
        "out": "/tmp/congdoandlvn_list.html",
        "wait_ms": 8000,
    },
]


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        )
        for d in DUMPS:
            page = await ctx.new_page()
            print(f"\n========== {d['name']} ==========", flush=True)
            print(f"  url: {d['url']}", flush=True)
            try:
                await page.goto(d["url"], wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(d["wait_ms"])
                html = await page.content()
                with open(d["out"], "w") as f:
                    f.write(html)
                print(f"  saved: {d['out']} ({len(html)} bytes)", flush=True)
                print(f"  page title: {(await page.title())[:80]}", flush=True)

                # Quick scan cho date markers
                if "article" in d["name"]:
                    import re
                    date_hints = []
                    for pat in [
                        r"<meta[^>]+(?:published|date|datetime)[^>]+content=['\"]([^'\"]+)['\"]",
                        r"class=['\"][^'\"]*(?:date|time|publish|update)[^'\"]*['\"][^>]*>([^<]{0,80})",
                        r"datetime=['\"]([^'\"]+)['\"]",
                        r"\d{1,2}[/-]\d{1,2}[/-]20\d{2}[\s\xa0]+\d{1,2}:\d{2}",
                    ]:
                        date_hints.extend(re.findall(pat, html, re.I)[:3])
                    print(f"  date hints (first 10): {date_hints[:10]}", flush=True)

                # Quick scan cho content containers (cho nbtpc)
                if "nbtpc" in d["name"]:
                    body_text_len = await page.evaluate(
                        """() => {
                          const candidates = [
                            'div.NormalContent', 'div.Content', 'td.News_FullStory',
                            '.ContentPanel', 'div.ArticleContent', 'td.ArticleContent',
                            'div.NewsContent', 'div.detail-news', 'div.NewsDetail',
                            'div.news-fulltext', 'div.body-content', 'div.ContentDetail',
                            'div[id*="ArticleBody"]', 'div[id*="NewsBody"]', 'div[id*="Content"]',
                          ];
                          const result = {};
                          candidates.forEach(sel => {
                            try {
                              const els = document.querySelectorAll(sel);
                              els.forEach((el, i) => {
                                const len = (el.innerText || '').length;
                                if (len > 100) result[`${sel}#${i}`] = len;
                              });
                            } catch (e) {}
                          });
                          return result;
                        }"""
                    )
                    print(f"  nbtpc candidate selectors with text >100 chars: {body_text_len}", flush=True)

                # Cho congdoandlvn — extract anchor sample qua getAttribute thay vì .href
                if "congdoandlvn" in d["name"]:
                    raw_hrefs = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.slice(0, 30).map(a => a.getAttribute('href'))",
                    )
                    print("  first 30 raw hrefs (getAttribute):", flush=True)
                    for h in raw_hrefs:
                        print(f"    {h}", flush=True)

            except Exception as e:
                print(f"  ERROR: {type(e).__name__}: {e}", flush=True)
            finally:
                await page.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
