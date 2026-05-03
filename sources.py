"""
Config nguồn JS-rendered cần Playwright. Mỗi nguồn:
- name: tên hiển thị (gắn với host, ví dụ "Mac Mini (npc.com.vn)")
- list_url: trang tin tức/section
- link_pattern: regex match pathname (sau urlparse) bài chi tiết
- content_selector: CSS selector cho khối nội dung bài (fallback sang article/main nếu None)
- wait_for: optional CSS selector chờ hiển thị trước khi extract (cho site lazy-load)
- wait_after_load_ms: thêm thời gian chờ sau khi load xong (default 2000ms),
  tăng lên cho React lazy-load (vd evnhanoi cần ~8000ms)

Patterns đã được audit thực tế ngày 2026-04-28 và bổ sung 2026-04-29 — xem audit_sources.py.
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
    wait_after_load_ms: int | None = None
    # Override user-agent (vd evnhcmc cần Googlebot UA để bypass Cloudflare bot block)
    user_agent: str | None = None


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
        name="evnhanoi.vn",
        # React SPA — chỉ root page mới render được news links sau ~6-8s
        list_url="https://evnhanoi.vn",
        link_pattern=r"^/cms/news/[a-z0-9-]+$",
        content_selector="div.news-content, div.article-content, article, main",
        wait_for="a[href*='/cms/news/']",
        wait_after_load_ms=8000,
    ),
    Source(
        name="evnfc.vn",
        list_url="https://www.evnfc.vn/tin-tuc",
        link_pattern=r"^/tin-chi-tiet/[a-z0-9-]+$",
        content_selector="div.article-content, div.detail-content, article, div.content",
        wait_for="a[href*='/tin-chi-tiet/']",
    ),
    Source(
        name="congdoandlvn.org.vn",
        list_url="https://www.congdoandlvn.org.vn/tin-tuc.htm",
        # Articles thật có slug ~80-110 ký tự; pages meta (truyen-thong-..., danh-muc-...) chỉ ~30-45.
        link_pattern=r"^/[a-z0-9-]{50,}\.htm$",
        content_selector="div.detail-content, div.article-content, div.news-content, article, div.content",
        wait_for="a[href$='.htm']",
        wait_after_load_ms=8000,
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
    # mientrungpid.com.vn — DISABLED 03/05/2026.
    # Audit B3a: list page load OK + 43 anchor unique, NHƯNG ID range chỉ 173-329
    # (bài cũ nhất 2018, mới nhất 2023). Site dormant, không có bài fresh trong
    # 3-day window → 0 article insert kể cả khi extractor work.
    # Source(
    #     name="mientrungpid.com.vn",
    #     list_url="https://mientrungpid.com.vn/tin-tuc/tin-tuc-nganh-dien",
    #     link_pattern=r"^/tin-chi-tiet/id/\d+/.+",
    #     content_selector="div.detail-content, div.article-content, article, div.content",
    #     wait_for="a[href*='/tin-chi-tiet/']",
    #     category="doanh-nghiep",
    # ),
    Source(
        name="nbtpc.com.vn",
        list_url="https://nbtpc.com.vn/c2/news-c/Tin-tuc-Hoat-dong-1.aspx",
        link_pattern=r"^/d4/news/[A-Za-z0-9-]+-\d+-\d+\.aspx$",
        content_selector="div.news-detail, div.article-content, article, div.content",
        wait_for="a[href*='/d4/news/']",
        category="doanh-nghiep",
        wait_after_load_ms=4000,
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

    Source(
        name="evnhcmc.vn",
        list_url="https://www.evnhcmc.vn/Tintuc",
        link_pattern=r"^/Tintuc/chitiet/\d+$",
        content_selector="div.detail-content, div.news-content, div.content-detail, article, main",
        wait_for="a[href*='/Tintuc/chitiet/']",
        wait_after_load_ms=4000,
        # Googlebot UA bypass Cloudflare "Access Restricted by Security Policy"
        # Site cho phép Googlebot trong robots.txt; reverse-DNS check không nghiêm trên endpoint này.
        user_agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    ),

    # --- Phase B3b: site mới có anti-bot, probe xác nhận khả thi 03/05/2026 ---
    Source(
        name="laodong.vn",
        list_url="https://laodong.vn/kinh-doanh",
        # Strict keyword filter — chỉ phrase đa-từ specific, KHÔNG dùng `dien` alone
        # vì false positive nặng: dien-bien (Điện Biên province), dien-tu (electronic),
        # dien-thoai (phone), dien-anh (cinema), dien-may (appliance), dien-vien (actor).
        link_pattern=r"^/[a-z0-9-]+/[^/]*(?:dien-luc|dien-gio|dien-mat-troi|dien-hat-nhan|dien-khi|dien-sinh-khoi|thuy-dien|nhiet-dien|nang-luong|evn|bess|cung-ung-dien|gia-dien|tiet-kiem-dien|luoi-dien|quy-hoach-dien|hydro-xanh)[^/]*-\d{6,8}\.ldo$",
        content_selector="div.art-body, div.article__body, div.detail-content, div.detail__content, article, main",
        wait_for="a[href$='.ldo']",
        wait_after_load_ms=5000,  # site nặng JS + nhiều CDN script (probe thấy 25+ resource)
        category="bao-chi",
    ),
    Source(
        name="qdnd.vn",
        list_url="https://www.qdnd.vn/kinh-te",
        # Same strict filter — round 2 thấy lọt "thuong-mai-dien-tu" (e-commerce).
        link_pattern=r"^/kinh-te/tin-tuc/[^/]*(?:dien-luc|dien-gio|dien-mat-troi|dien-hat-nhan|dien-khi|dien-sinh-khoi|thuy-dien|nhiet-dien|nang-luong|evn|bess|cung-ung-dien|gia-dien|tiet-kiem-dien|luoi-dien|quy-hoach-dien|hydro-xanh)[^/]*-\d{6,7}$",
        content_selector="div.detail-content, div.article-content, div.news-content, div.article__body, div.entry-content, article, main",
        wait_for="a[href*='/kinh-te/tin-tuc/']",
        wait_after_load_ms=4000,
        category="bao-chi",
    ),
    Source(
        name="cpc.vn",
        # Site redirect /tin-tuc → /tin-tuc-su-kien. Trỏ thẳng để skip 1 hop.
        list_url="https://cpc.vn/vi-vn/tin-tuc-su-kien",
        # DotNetNuke article URL: /vi-vn/Tin-tuc-su-kien/Tin-tuc-chi-tiet/articleId/<id>
        # CPC = EVN miền Trung → toàn bài điện, không cần keyword filter
        link_pattern=r"^/vi-vn/Tin-tuc-su-kien/Tin-tuc-chi-tiet/articleId/\d+$",
        content_selector="div.detail-content, div.news-detail, div.article-content, article, main",
        wait_for="a[href*='/Tin-tuc-chi-tiet/']",
        wait_after_load_ms=4000,
        category="co-quan",
    ),

    # --- TODO: NPT (npt.com.vn) ---
    # Probe 03/05/2026: D1N cookie auto-handled OK, nhưng list URL
    # /tin-tuc-su-kien.html → 404. Cần probe path đúng (.aspx? /news? root?)
    # trước khi thêm Source entry. Defer follow-up.

    # --- Đã loại bỏ (audit 2026-04-28/29) ---
    # xaylapdien.net    : toàn static service pages, no published_at, waste ~16s/run
]
