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

from db import (
    existing_hashes,
    fetch_playwright_sources_from_db,
    insert_article,
    update_source_crawled,
    update_virtual_source_crawled,
    virtual_source_id,
)
from extractor import Article, crawl_all
from sources import SOURCES, Source
from summarizer import is_invalid_summary, summarize, word_count

THREE_DAYS = timedelta(days=3)


def _row_to_source(row: dict) -> Source | None:
    """
    Convert DB row (electricity_sources feed_type='playwright') → Source dataclass.
    Trả None nếu config thiếu link_pattern (DB row hỏng).

    scraper_config jsonb format Phase E auto-handover dùng:
        {list_url, link_pattern, content_selector, category, wait_after_load_ms, wait_for, user_agent}
    """
    cfg = row.get("scraper_config") or {}
    link_pattern = cfg.get("link_pattern")
    if not link_pattern:
        return None

    name = row.get("name") or row.get("base_url", "unknown")
    if not name.startswith("Mac Mini"):
        # Phase E đã đặt name kiểu "Mac Mini (domain.tld)" — defensive cho rows cũ
        host = name
        try:
            from urllib.parse import urlparse
            host = urlparse(row.get("base_url", "")).netloc.replace("www.", "") or name
        except Exception:
            pass
        name = f"Mac Mini ({host})"

    list_url = cfg.get("list_url") or row.get("list_url") or row.get("base_url")
    if not list_url:
        return None

    return Source(
        name=name,
        list_url=list_url,
        link_pattern=link_pattern,
        content_selector=cfg.get("content_selector"),
        wait_for=cfg.get("wait_for"),
        category=cfg.get("category", "bao-chi"),
        wait_after_load_ms=cfg.get("wait_after_load_ms"),
        user_agent=cfg.get("user_agent"),
    )


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

    # Merge static sources (sources.py legacy) + DB-driven Playwright sources
    # (Phase E auto-handover). DB rows có scraper_config jsonb — convert sang
    # Source dataclass. DB ưu tiên override sources.py nếu trùng name.
    static_sources = list(SOURCES)
    db_sources: list[Source] = []
    db_id_by_name: dict[str, str] = {}
    try:
        db_rows = fetch_playwright_sources_from_db()
        for row in db_rows:
            s = _row_to_source(row)
            if s:
                db_sources.append(s)
                if row.get("id"):
                    db_id_by_name[s.name] = row["id"]
    except Exception as e:
        print(f"[warn] DB Playwright sources fetch failed: {e} — fallback sources.py only", flush=True)

    static_names = {s.name for s in static_sources}
    db_only = [s for s in db_sources if s.name not in static_names]
    all_sources = static_sources + db_only

    print(
        f"[start] {datetime.now(timezone.utc).isoformat()}  "
        f"sources={len(all_sources)} (static={len(static_sources)} + db_handover={len(db_only)})",
        flush=True,
    )

    # Per-source id resolver cho insert_article. Static sources đều dùng virtual
    # "Mac Mini Scraper" id. DB handover sources dùng id riêng (đã có sẵn trong row).
    src_id_by_name: dict[str, str] = dict(db_id_by_name)

    # Crawl all sources via Playwright
    articles = await crawl_all(all_sources)
    print(f"[crawl] {len(articles)} articles fetched total", flush=True)

    # Mark per-source last_crawled_at cho Playwright handover rows (kể cả 0 bài
    # insert được). Pipeline-health-check dùng field này để alert "6h chưa xử lý".
    for name, sid in db_id_by_name.items():
        try:
            update_source_crawled(sid)
        except Exception as e:
            print(f"  [warn] update_source_crawled({name}): {e}", flush=True)

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

            # Pick source_id: DB handover row có id riêng, static dùng virtual id
            article_src_id = src_id_by_name.get(art.source_name, src_id)

            # Compute source_domain để Phase E discover-candidates tự skip
            # những domain Mac Mini đã cover (knownDomains derive từ field này).
            from urllib.parse import urlparse
            try:
                host = urlparse(art.url).hostname or ""
                if host.startswith("www."):
                    host = host[4:]
                source_domain = host or None
            except Exception:
                source_domain = None

            ok = insert_article({
                "source_id": article_src_id,
                "source_name": art.source_name,
                "source_category": art.source_category,
                "source_domain": source_domain,
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
