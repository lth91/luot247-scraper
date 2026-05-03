"""
Debug B3a — chạy thẳng pipeline extractor.crawl_source trên 4 site broken.
Dump title/content_len/published_at cho từng article fetched → biết bug ở đâu
(content selector miss? date parse fail? content quá ngắn?).

Chạy:
    source ~/.openclaw/venv-luot247/bin/activate
    python debug_b3a.py 2>&1 | tee /tmp/debug_b3a.log
"""
from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

from extractor import crawl_source
from sources import SOURCES

B3A_NAMES = {"npc.com.vn", "congdoandlvn.org.vn", "mientrungpid.com.vn", "nbtpc.com.vn"}


async def main() -> None:
    targets = [s for s in SOURCES if s.name in B3A_NAMES]
    print(f"Debug crawl {len(targets)} site(s)...", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for src in targets:
                print(f"\n========== {src.name} ==========", flush=True)
                print(f"list_url: {src.list_url}", flush=True)
                print(f"content_selector: {src.content_selector}", flush=True)
                try:
                    articles = await crawl_source(browser, src)
                    print(f"  [{src.name}] returned {len(articles)} article(s)", flush=True)
                    for i, a in enumerate(articles):
                        print(f"\n  [{i}] {a.url}", flush=True)
                        print(f"      title: {a.title[:100]}", flush=True)
                        print(f"      content len: {len(a.content)}", flush=True)
                        print(f"      content preview: {a.content[:200]}", flush=True)
                        print(f"      published_at: {a.published_at}", flush=True)
                except Exception as e:
                    print(f"  FATAL: {type(e).__name__}: {e}", flush=True)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
