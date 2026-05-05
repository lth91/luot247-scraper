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

# LƯU Ý: Mac Mini Python regex STRICTER hơn TS edge functions có lý do:
#   • Edge function (discovery-rss-news, crawl-electricity-news) có LLM
#     classifier làm second pass — keyword broad là OK vì LLM lọc lại.
#   • Mac Mini Playwright KHÔNG có LLM second pass → keyword là tầng filter
#     duy nhất. Nếu broad sẽ insert nhiều bài "có nhắc đến điện" nhưng chủ
#     đề khác (báo cáo IIP, tin chính trị, BCT làm việc HR, v.v.).
#   • Drop khỏi TS canonical: "năng lượng" (quá broad — cover dầu/khí/than),
#     "Bộ Công Thương" (cover commerce/HR/industry, không chỉ điện).
ELECTRICITY_KEYWORD_RE = re.compile(
    r"\b(EVN|BESS|"
    r"điện(?!\s*(thoại|tử|ảnh|máy|tử|đàm|văn|tín))|"
    r"điện\s*lực|điện\s*gió|điện\s*mặt\s*trời|điện\s*hạt\s*nhân|điện\s*sinh\s*khối|"
    r"thủy\s*điện|nhiệt\s*điện|"
    r"lưới\s*điện|cung\s*ứng\s*điện|giá\s*điện|tiết\s*kiệm\s*điện|"
    r"pin\s*lưu\s*trữ|lưu\s*trữ\s*điện|pin\s*(natri|lithium|li-?ion)|"
    r"hydro\s*xanh|xe\s*điện|"
    r"Cục\s*Điện\s*lực|"
    r"NLTT|Quy\s*hoạch\s*điện)",
    re.IGNORECASE,
)


def is_electricity_topical(text: str) -> bool:
    """True nếu text chứa từ khoá ngành điện VN.

    QUAN TRỌNG: chỉ áp dụng vào TITLE, không content. Lý do: bài kinh tế/chính
    trị thường có 1-2 mention "điện" hoặc "Bộ Công Thương" lệch chủ đề trong
    content, nhưng title sẽ phản ánh chủ đề chính. Title-only filter giảm
    false positive đáng kể.
    """
    if not text:
        return False
    return bool(ELECTRICITY_KEYWORD_RE.search(text))
