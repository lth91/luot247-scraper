"""
Audit script — không insert DB. Mở từng list page bằng Playwright,
in ra 12 href unique cùng host (để eyeball pattern), kèm tổng số <a>
và một số metric phụ trợ.

Chạy:
    source ~/.openclaw/venv-luot247/bin/activate
    python audit_sources.py 2>&1 | tee /tmp/audit.log
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from sources import SOURCES


async def audit_site(pw, src) -> None:
    print(f"\n========== {src.name} ==========", flush=True)
    print(f"list_url: {src.list_url}", flush=True)
    print(f"current pattern: {src.link_pattern}", flush=True)

    browser = await pw.chromium.launch(headless=True)
    ctx = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    page = await ctx.new_page()
    try:
        try:
            await page.goto(src.list_url, wait_until="domcontentloaded", timeout=25000)
        except Exception as e:
            print(f"  GOTO ERROR: {e}", flush=True)
            return

        # Wait a bit for JS render
        try:
            if src.wait_for:
                await page.wait_for_selector(src.wait_for, timeout=8000)
            else:
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        host = urlparse(src.list_url).hostname or ""
        anchors = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(a => a.href)",
        )
        print(f"  total <a href>: {len(anchors)}", flush=True)

        same_host: list[str] = []
        for h in anchors:
            try:
                u = urlparse(h)
                if (u.hostname or "").endswith(host.lstrip("www.")) or u.hostname == host:
                    same_host.append(u.path)
            except Exception:
                continue

        # Dedupe + remove empty/root
        uniq_paths = list(dict.fromkeys(p for p in same_host if p and p != "/"))
        print(f"  unique same-host paths: {len(uniq_paths)}", flush=True)

        # Pathlength distribution (helps spot article URLs which tend to be long)
        lens = Counter(len(p) for p in uniq_paths)
        print(f"  path length histogram: {sorted(lens.items())}", flush=True)

        # Print sample of LONGEST paths first (likely articles)
        sample = sorted(uniq_paths, key=len, reverse=True)[:15]
        print("  longest 15 paths:", flush=True)
        for p in sample:
            print(f"    {p}", flush=True)

        # Page title for sanity
        title = await page.title()
        print(f"  page title: {title[:80]}", flush=True)

    finally:
        await browser.close()


async def main() -> None:
    # Optional filter: python audit_sources.py npc evnhanoi
    only = set(sys.argv[1:])
    targets = [s for s in SOURCES if not only or s.name in only or any(o in s.name for o in only)]
    print(f"Auditing {len(targets)} site(s)...", flush=True)

    async with async_playwright() as pw:
        for src in targets:
            try:
                await audit_site(pw, src)
            except Exception as e:
                print(f"  FATAL on {src.name}: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
