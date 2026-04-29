"""
Entry point: load env, crawl all sources, summarize bài mới, insert vào Supabase.

Chạy:
    SUPABASE_URL=... SUPABASE_SECRET_KEY=... ANTHROPIC_API_KEY=... python scraper.py

Hoặc qua deploy/run.sh trên Mac Mini.
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Auto-load .env nếu chạy local (Mac Mini dùng env từ LaunchAgent plist)
try:
    from dotenv import load_dotenv

    env_path = Path(os.environ.get("LUOT247_ENV", Path.home() / ".openclaw" / "luot247-scraper.env"))
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from db import existing_hashes, insert_article, update_virtual_source_crawled, virtual_source_id
from extractor import Article, crawl_all
from sources import SOURCES
from summarizer import is_invalid_summary, summarize, word_count

THREE_DAYS = timedelta(days=3)


def is_too_old(published_at: str | None) -> bool:
    if not published_at:
        return False
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - dt > THREE_DAYS
    except Exception:
        return False


async def main() -> int:
    # Validate env
    for var in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "ANTHROPIC_API_KEY"):
        if not os.environ.get(var):
            print(f"FATAL: env {var} missing", flush=True)
            return 2

    src_id = virtual_source_id()
    if not src_id:
        print("FATAL: virtual source 'Mac Mini Scraper' not in electricity_sources. "
              "Apply migration luot247-vision/supabase/migrations/*_add_macmini_scraper_source.sql", flush=True)
        return 2

    print(f"[start] {datetime.now(timezone.utc).isoformat()}  sources={len(SOURCES)}", flush=True)

    # Crawl all sources via Playwright
    articles = await crawl_all(SOURCES)
    print(f"[crawl] {len(articles)} articles fetched total", flush=True)

    if not articles:
        update_virtual_source_crawled()
        return 0

    # Skip too old (>3 days)
    fresh = [a for a in articles if not is_too_old(a.published_at)]
    print(f"[filter] {len(fresh)} after 3-day window (dropped {len(articles) - len(fresh)})", flush=True)

    # Dedupe vs DB
    hashes = [a.url_hash for a in fresh]
    in_db = existing_hashes(hashes)
    new_arts = [a for a in fresh if a.url_hash not in in_db]
    print(f"[dedupe] {len(new_arts)} new (skip {len(fresh) - len(new_arts)} already in DB)", flush=True)

    # Summarize + insert
    inserted = 0
    skipped = 0
    for art in new_arts:
        try:
            known_date = art.published_at[:10] if art.published_at else None
            res = summarize(art.title, art.content, known_date)
            summary = res["summary"]
            llm_date = res["published_date"]

            if not summary:
                print(f"  empty summary: {art.url}", flush=True)
                skipped += 1
                continue
            if is_invalid_summary(summary):
                print(f"  invalid (apology): {art.url}", flush=True)
                skipped += 1
                continue

            # Final published_at: prefer meta, else LLM (kèm safety check).
            # Safety: nếu extractor không tìm thấy date, KHÔNG tin LLM nói "today"
            # hay future date — đó thường là hallucination khi prompt mặc định
            # năm hiện tại cho dates không có năm trong content.
            pub = art.published_at
            if not pub and llm_date:
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if llm_date >= today:
                    print(f"  reject LLM date (today/future, no metadata): {llm_date} {art.url}", flush=True)
                    skipped += 1
                    continue
                pub = f"{llm_date}T00:00:00+00:00"
            if not pub:
                print(f"  no published_at: {art.url}", flush=True)
                skipped += 1
                continue
            if is_too_old(pub):
                print(f"  too old after LLM: {art.url}", flush=True)
                skipped += 1
                continue

            ok = insert_article({
                "source_id": src_id,
                "source_name": art.source_name,
                "source_category": art.source_category,
                "title": art.title,
                "summary": summary,
                "original_url": art.url,
                "url_hash": art.url_hash,
                "published_at": pub,
                "summary_word_count": word_count(summary),
            })
            if ok:
                inserted += 1
                print(f"  inserted: {art.title[:80]}", flush=True)
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR {art.url}: {e}", flush=True)
            traceback.print_exc()
            skipped += 1

    update_virtual_source_crawled()
    print(f"[done] inserted={inserted} skipped={skipped}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
