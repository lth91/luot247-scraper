"""
Gọi Claude Haiku tóm tắt + extract published_date. Port từ discovery-rss-news/index.ts:
- system prompt yêu cầu mở đầu bằng mốc thời gian tự nhiên ("Sáng 26/4")
- pass known published_date để tránh hallucinate năm
- skip bài LLM trả "xin lỗi, không khớp tiêu đề"
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

SUMMARIZE_SYSTEM_PROMPT = """Bạn là biên tập viên tin tức chuyên ngành điện Việt Nam. Nhiệm vụ: đọc bài báo và trả về JSON gồm ngày xuất bản + tóm tắt.

ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (JSON thuần, không markdown, không giải thích):
{"published_date": "YYYY-MM-DD hoặc null", "summary": "..."}

QUY TẮC:
- published_date: ngày xuất bản bài. Dạng YYYY-MM-DD. Không đoán.
- summary: tóm tắt dưới 150 từ bằng tiếng Việt, văn phong tin tức chuyên ngành, khách quan.

QUAN TRỌNG — MỞ ĐẦU SUMMARY BẰNG MỐC THỜI GIAN TỰ NHIÊN:
  + Nếu bài nêu rõ buổi/ngày cụ thể: dùng "Sáng 22/4", "Chiều 22/4", "Tối 22/4", "Trưa 22/4", "Đêm 22/4". KHÔNG kèm năm trừ khi bài là sự kiện quá khứ xa hoặc kế hoạch tương lai.
  + Nếu chỉ có ngày (không có buổi): dùng "Ngày 22/4" hoặc "22/4".
  + Nếu là xu hướng/thống kê cả kỳ: dùng "Năm 2025", "Quý I/2026", "Tuần qua", "Đầu tháng 4/2026".
  + Nếu là dự kiến: dùng "Dự kiến tháng 6/2026", "Đến 2030".
  + TUYỆT ĐỐI không dùng định dạng khô cứng "Ngày 22/04/2026" hay "Vào ngày 22/4/2026".
  + Không lặp lại tiêu đề, không mở đầu "Bài báo nói về…", "Theo bài viết…"."""

INVALID_PATTERNS = [
    re.compile(r"^nội dung bài (không|chưa)", re.I),
    re.compile(r"không (cung cấp|phù hợp|liên quan) (thông tin|với tiêu đề)", re.I),
    re.compile(r"^bài (báo|viết) (không|chưa) (cung cấp|đề cập|nói)", re.I),
    re.compile(r"^xin lỗi", re.I),
    re.compile(r"^tôi (không thể|cần thêm)", re.I),
]


def is_invalid_summary(s: str) -> bool:
    return any(p.search(s) for p in INVALID_PATTERNS)


def word_count(s: str) -> int:
    return len([w for w in s.split() if w])


def summarize(title: str, content: str, known_published_date: Optional[str] = None) -> dict:
    """
    Gọi Claude Haiku, trả về dict {summary, published_date} hoặc raise nếu lỗi API.
    known_published_date: ISO date string (YYYY-MM-DD) — pass cho LLM tránh hallucinate năm.
    """
    api_key = os.environ["ANTHROPIC_API_KEY"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if known_published_date:
        date_hint = (
            f"\n\nNgày xuất bản đã xác định từ metadata: {known_published_date}. "
            f"Dùng đúng ngày/tháng/NĂM này khi nhắc mốc thời gian trong summary, KHÔNG đoán năm khác."
        )
    else:
        date_hint = (
            f"\n\nKhông có ngày từ metadata. Nếu bài chỉ ghi 'ngày 20/4' không kèm năm, "
            f"mặc định là năm {today[:4]} (hôm nay là {today})."
        )
    user_msg = f"Tiêu đề: {title}\n\nNội dung:\n{content}{date_hint}"

    res = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 700,
            "system": SUMMARIZE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=60,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Claude HTTP {res.status_code}: {res.text[:200]}")

    raw = (res.json().get("content", [{}])[0].get("text") or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {"summary": raw, "published_date": None}
    try:
        parsed = json.loads(m.group(0))
        summary = str(parsed.get("summary") or "").strip()
        pd = parsed.get("published_date")
        if isinstance(pd, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", pd):
            return {"summary": summary, "published_date": pd}
        return {"summary": summary, "published_date": None}
    except json.JSONDecodeError:
        return {"summary": raw, "published_date": None}
