"""
Supabase REST helpers. Dùng sb_secret_* (Authorization Bearer + apikey) để bypass RLS,
insert vào electricity_news. Dedup bằng url_hash.
"""

from __future__ import annotations

import os
from typing import Iterable

import requests


def _headers() -> dict:
    key = os.environ["SUPABASE_SECRET_KEY"]
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "return=minimal",
    }


def _base_url() -> str:
    return os.environ["SUPABASE_URL"].rstrip("/")


def existing_hashes(hashes: Iterable[str]) -> set[str]:
    """Trả về subset hashes đã có trong DB (skip ngay những bài này)."""
    hs = list(hashes)
    if not hs:
        return set()
    # PostgREST in.() filter
    quoted = ",".join(f'"{h}"' for h in hs)
    url = f"{_base_url()}/rest/v1/electricity_news?select=url_hash&url_hash=in.({quoted})"
    res = requests.get(url, headers=_headers(), timeout=20)
    res.raise_for_status()
    return {r["url_hash"] for r in res.json()}


def virtual_source_id(name: str = "Mac Mini Scraper") -> str | None:
    """Lookup virtual source row id để gắn FK. Nếu chưa có, trả None."""
    url = f"{_base_url()}/rest/v1/electricity_sources?select=id&name=eq.{name}"
    res = requests.get(url, headers=_headers(), timeout=15)
    if res.status_code != 200:
        return None
    rows = res.json()
    return rows[0]["id"] if rows else None


def insert_article(art_dict: dict) -> bool:
    """
    Insert vào electricity_news. art_dict cần đủ fields:
      source_id, source_name, source_category, title, summary, original_url,
      url_hash, published_at, summary_word_count
    Trả True nếu insert thành công, False nếu duplicate (409) hoặc lỗi.
    """
    res = requests.post(
        f"{_base_url()}/rest/v1/electricity_news",
        headers=_headers(),
        json=art_dict,
        timeout=20,
    )
    if res.status_code in (200, 201):
        return True
    if res.status_code == 409 or "duplicate" in res.text.lower():
        return False
    print(f"  insert failed HTTP {res.status_code}: {res.text[:200]}", flush=True)
    return False


def update_virtual_source_crawled() -> None:
    """Update last_crawled_at trên virtual source row (nếu có)."""
    sid = virtual_source_id()
    if not sid:
        return
    from datetime import datetime, timezone

    requests.patch(
        f"{_base_url()}/rest/v1/electricity_sources?id=eq.{sid}",
        headers=_headers(),
        json={
            "last_crawled_at": datetime.now(timezone.utc).isoformat(),
            "consecutive_failures": 0,
            "last_error": None,
        },
        timeout=15,
    )
