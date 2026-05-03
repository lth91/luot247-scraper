"""
Probe 4 site candidate cho Phase B3b — chưa có entry trong sources.py.
Nhiệm vụ: confirm Playwright truy cập được, dump anchor sample để eyeball pattern,
trace redirect chain (cho QĐND), inspect cookie set sau navigation (cho NPT/Lao Động D1N).

Chạy:
    source ~/.openclaw/venv-luot247/bin/activate
    python probe_new_sites.py 2>&1 | tee /tmp/probe_b3b.log

Sau khi có output → sửa `sources.py` thêm entries cho site nào confirm khả thi.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from urllib.parse import urlparse

from playwright.async_api import async_playwright


# Candidates từ luot247-scraper#1 + audit luot247-vision Phase A
CANDIDATES = [
    {
        "name": "NPT (Tổng công ty Truyền tải điện)",
        "list_url": "https://www.npt.com.vn/tin-tuc-su-kien.html",
        "fallback_list_urls": ["https://www.npt.com.vn", "https://www.npt.com.vn/tin-tuc.html"],
        "expected_anti_bot": "D1N cookie + reload script",
        "wait_after_load_ms": 8000,
    },
    {
        "name": "Lao Động",
        "list_url": "https://laodong.vn/kinh-doanh",
        "fallback_list_urls": ["https://laodong.vn/rss/dien-3-c", "https://laodong.vn"],
        "expected_anti_bot": "D1N cookie",
        "wait_after_load_ms": 6000,
    },
    {
        "name": "Báo Quân Đội Nhân Dân",
        "list_url": "https://www.qdnd.vn/kinh-te",
        "fallback_list_urls": ["https://qdnd.vn/kinh-te", "https://www.qdnd.vn"],
        "expected_anti_bot": "302 redirect loop",
        "wait_after_load_ms": 6000,
    },
    {
        "name": "EVN miền Trung / CPC",
        "list_url": "https://cpc.vn/vi-vn/tin-tuc",
        "fallback_list_urls": ["https://cpc.vn", "https://www.cpc.vn/vi-vn/tin-tuc"],
        "expected_anti_bot": "Connection reset trên Edge IP (Supabase) — Mac Mini home IP có thể work",
        "wait_after_load_ms": 4000,
    },
]


async def probe_site(pw, c) -> None:
    name = c["name"]
    print(f"\n========== {name} ==========", flush=True)
    print(f"primary list_url: {c['list_url']}", flush=True)
    print(f"expected challenge: {c['expected_anti_bot']}", flush=True)

    browser = await pw.chromium.launch(headless=True)
    ctx = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    page = await ctx.new_page()

    # Trace redirect chain — quan trọng cho QĐND (302 loop)
    redirect_chain: list[str] = []
    page.on("response", lambda r: redirect_chain.append(f"  → {r.status} {r.url[:120]}"))

    # Try primary URL, fallback nếu fail
    urls_to_try = [c["list_url"]] + c.get("fallback_list_urls", [])
    success_url = None
    for url in urls_to_try:
        redirect_chain.clear()
        try:
            print(f"\n  TRY: {url}", flush=True)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            success_url = url
            break
        except Exception as e:
            print(f"  GOTO FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
            print(f"  redirect chain ({len(redirect_chain)} hops):", flush=True)
            for r in redirect_chain[:8]:
                print(r, flush=True)

    if not success_url:
        print("  ❌ ALL URLS FAILED", flush=True)
        await browser.close()
        return

    print(f"  ✓ Loaded: {success_url}", flush=True)
    print(f"  redirect chain ({len(redirect_chain)} hops):", flush=True)
    for r in redirect_chain[:8]:
        print(r, flush=True)

    # Wait for JS render + cookies
    await page.wait_for_timeout(c["wait_after_load_ms"])

    # Inspect cookies
    cookies = await ctx.cookies()
    cookie_names = [ck["name"] for ck in cookies]
    print(f"\n  cookies set ({len(cookies)}): {cookie_names[:15]}", flush=True)
    # D1N pattern check
    d1n_keys = [n for n in cookie_names if "d1n" in n.lower() or "challenge" in n.lower()]
    if d1n_keys:
        print(f"  D1N/challenge cookies: {d1n_keys}", flush=True)

    # Page sanity
    title = await page.title()
    print(f"  page title: {title[:80]}", flush=True)

    # Dump same-host anchors
    host = urlparse(success_url).hostname or ""
    anchors = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(a => a.href)",
    )
    print(f"\n  total <a href>: {len(anchors)}", flush=True)

    same_host: list[str] = []
    for h in anchors:
        try:
            u = urlparse(h)
            host_strip = host.lstrip("www.")
            if (u.hostname or "").endswith(host_strip) or u.hostname == host:
                same_host.append(u.path)
        except Exception:
            continue

    uniq_paths = list(dict.fromkeys(p for p in same_host if p and p != "/"))
    print(f"  unique same-host paths: {len(uniq_paths)}", flush=True)

    # Path length histogram → giúp pick threshold cho regex
    lens = Counter(len(p) for p in uniq_paths)
    print(f"  path length histogram: {sorted(lens.items())}", flush=True)

    # Sample longest paths (likely article URLs)
    sample = sorted(uniq_paths, key=len, reverse=True)[:20]
    print("  longest 20 paths:", flush=True)
    for p in sample:
        print(f"    {p}", flush=True)

    await browser.close()


async def main() -> None:
    print(f"Probing {len(CANDIDATES)} candidate sites for B3b...", flush=True)
    async with async_playwright() as pw:
        for c in CANDIDATES:
            try:
                await probe_site(pw, c)
            except Exception as e:
                print(f"  FATAL on {c['name']}: {type(e).__name__}: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
