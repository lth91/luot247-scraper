"""
Config nguồn JS-rendered cần Playwright. Mỗi nguồn:
- name: tên hiển thị (gắn với host, ví dụ "Mac Mini (npc.com.vn)")
- list_url: trang tin tức/section
- link_pattern: regex match pathname (sau urlparse) bài chi tiết
- content_selector: CSS selector cho khối nội dung bài (fallback sang article/main nếu None)
- wait_for: optional CSS selector chờ hiển thị trước khi extract (cho site lazy-load)

Patterns đã được audit thực tế ngày 2026-04-28 — xem audit_sources.py.
"""

from dataclasses import dataclass


@dataclass
class Source:
    name: str
    list_url: str
    link_pattern: str
    content_selector: str | None = None
    wait_for: str | None = None
    category: str = "co-quan"  # co-quan | doanh-nghiep | bao-chi


SOURCES: list[Source] = [
    # --- EVN family (cơ quan) ---
    Source(
        name="npc.com.vn",
        list_url="https://npc.com.vn/tin-tuc-nganh-dien/",
        link_pattern=r"^/tin-tuc-nganh-dien/[a-z0-9-]+-\d+\.html$",
        content_selector="div.detail-content, div.news-detail, article, div.content-detail",
        wait_for="a[href*='/tin-tuc-nganh-dien/']",
    ),
    Source(
        name="evnfc.vn",
        list_url="https://www.evnfc.vn/tin-tuc",
        link_pattern=r"^/tin-chi-tiet/[a-z0-9-]+$",
        content_selector="div.article-content, div.detail-content, article, div.content",
        wait_for="a[href*='/tin-chi-tiet/']",
    ),

    # --- Doanh nghiệp ---
    Source(
        name="pecc1.com.vn",
        list_url="https://www.pecc1.com.vn",
        link_pattern=r"^/d4/news/[A-Za-z0-9-]+-\d+-\d+\.aspx$",
        content_selector="div.news-detail, div.article-content, article, div.content",
        wait_for="a[href*='/d4/news/']",
        category="doanh-nghiep",
    ),
    Source(
        name="mientrungpid.com.vn",
        list_url="https://mientrungpid.com.vn/tin-tuc/tin-tuc-nganh-dien",
        link_pattern=r"^/tin-chi-tiet/id/\d+/.+",
        content_selector="div.detail-content, div.article-content, article, div.content",
        wait_for="a[href*='/tin-chi-tiet/']",
        category="doanh-nghiep",
    ),
    Source(
        name="xaylapdien.net",
        # Slug-only paths, no .html. Pattern requires keyword + length to avoid category pages.
        list_url="https://xaylapdien.net/tin-tuc-nganh-dien-moi-nhat",
        link_pattern=r"^/[a-z0-9-]{30,}$",
        content_selector="div.article-content, div.entry-content, article, div.post-content, div.detail",
        wait_for="a",
        category="doanh-nghiep",
    ),

    # --- Báo chí ---
    Source(
        name="dienvadoisong.vn",
        list_url="https://dienvadoisong.vn",
        # Format: /d/vi-VN/news/<slug>-60-3569-511378  (3 số ID cuối, không .html)
        link_pattern=r"^/d/vi-VN/news[a-z-]*/[A-Za-z0-9-]+-\d+-\d+-\d+$",
        content_selector="div.detail-content, div.news-detail, article.fck_detail, article, div.content",
        wait_for="a[href*='/d/vi-VN/news']",
        category="bao-chi",
    ),
    Source(
        name="nangluongsachvietnam.vn",
        list_url="https://nangluongsachvietnam.vn/c3/vi-VN/news-l/Dien-6-166",
        # Format: /d6/vi-VN/news/<slug>-6-166-33886
        link_pattern=r"^/d6/vi-VN/news/[A-Za-z0-9-]+-\d+-\d+-\d+$",
        content_selector="div.news-detail, div.detail-content, article, div.content",
        wait_for="a[href*='/d6/vi-VN/news/']",
        category="bao-chi",
    ),
    Source(
        name="icon.com.vn",
        list_url="https://icon.com.vn/vn/Trang-chu",
        # Format: /d6/vi-VN/news/<slug>-60-621-214135
        link_pattern=r"^/d6/vi-VN/news/[A-Za-z0-9-]+-\d+-\d+-\d+$",
        content_selector="div.news-detail, div.detail-content, article, div.content",
        wait_for="a[href*='/d6/vi-VN/news/']",
        category="bao-chi",
    ),
    Source(
        name="theleader.vn",
        list_url="https://theleader.vn/tieu-diem-channel387",
        # Filter focused on electricity to avoid off-topic content from a generic news channel.
        link_pattern=r"^/[^/]*(?:dien|nang-luong|evn|bess)[^/]*-d\d+\.html$",
        content_selector="div.detail__content, div.fck_detail, article, div.content-detail",
        wait_for="a[href*='-d']",
        category="bao-chi",
    ),

    # --- TODO: chưa scrape được, cần fix riêng (audit 2026-04-28) ---
    # evnhcmc.vn        : "Access Restricted by Security Policy" — bot block, cần stealth/proxy
    # evnhanoi.vn       : React SPA, JS chỉ render dashboard menu — cần wait_for cụ thể hơn
    # nbtpc.com.vn      : 0 anchor sau JS render — cần probe tiếp
    # congdoandlvn.org.vn: 0 anchor sau JS render — cần probe tiếp
]
