"""
Vietnamese electricity/energy keyword regex — topical pre-filter.

Mirror của luot247-vision/supabase/functions/_shared/electricity-keywords.ts
(giữ 2 nơi đồng bộ qua single source of truth — TypeScript là canonical,
file này phải sync khi đổi keywords).

Dùng cho Mac Mini Playwright scraper để filter homepage báo general
(znews.vn, plo.vn, vietnam.vn, …) — chỉ giữ bài điện/năng lượng trước khi
summarize. Static sources trong sources.py KHÔNG cần filter (đã curated).
"""

from __future__ import annotations

import re

ELECTRICITY_KEYWORD_RE = re.compile(
    r"\b(EVN|BESS|"
    r"điện(?!\s*(thoại|tử|ảnh|máy))|"
    r"năng\s*lượng|"
    r"điện\s*lực|điện\s*gió|điện\s*mặt\s*trời|điện\s*hạt\s*nhân|điện\s*sinh\s*khối|"
    r"thủy\s*điện|nhiệt\s*điện|"
    r"lưới\s*điện|cung\s*ứng\s*điện|giá\s*điện|tiết\s*kiệm\s*điện|"
    r"pin\s*lưu\s*trữ|lưu\s*trữ\s*điện|pin\s*(natri|lithium|li-?ion)|"
    r"hydro\s*xanh|xe\s*điện|"
    r"Bộ\s*Công\s*Thương|Cục\s*Điện\s*lực|"
    r"NLTT|PPA|DPPA|Quy\s*hoạch\s*điện)",
    re.IGNORECASE,
)


def is_electricity_topical(text: str) -> bool:
    """True nếu text chứa từ khoá liên quan điện/năng lượng VN."""
    if not text:
        return False
    return bool(ELECTRICITY_KEYWORD_RE.search(text))
