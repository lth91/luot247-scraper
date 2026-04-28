"""
Config 13 nguồn JS-rendered cần Playwright. Mỗi nguồn:
- name: tên hiển thị (gắn với host, ví dụ "Mac Mini (npc.com.vn)")
- list_url: trang tin tức/section
- link_pattern: regex match href bài chi tiết (sau khi resolve thành absolute URL — chỉ check pathname)
- content_selector: CSS selector cho khối nội dung bài (fallback sang article/main nếu None)
- wait_for: optional CSS selector chờ hiển thị trước khi extract (cho site lazy-load)
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
        list_url="https://npc.com.vn/View/tin-tuc/tin-chuyen-nganh/list",
        link_pattern=r"/View/tin-tuc/.+/[^/]+\.html?$",
        content_selector="div.news-detail, article.news-content, div.content-detail",
        wait_for="a[href*='/View/tin-tuc/']",
    ),
    Source(
        name="evnhanoi.vn",
        list_url="https://evnhanoi.vn/cms/category?k=tin-chuyen-nganh",
        link_pattern=r"/cms/[^/?]+/[a-z0-9-]{20,}",
        content_selector="div.detail-content, article.cms-detail, div.news-content",
        wait_for="a[href*='/cms/']",
    ),
    Source(
        name="evnhcmc.vn",
        list_url="https://www.evnhcmc.vn/tin-tuc",
        link_pattern=r"/tin-tuc/.+-\d+\.html",
        content_selector="div.detail, article, div.content-detail",
        wait_for="a[href*='/tin-tuc/']",
    ),
    Source(
        name="evnfc.vn",
        list_url="https://www.evnfc.vn/tin-tuc",
        link_pattern=r"/tin-tuc/[a-z0-9-]{20,}",
        content_selector="div.article-content, article, div.content",
        wait_for="a",
    ),
    Source(
        name="congdoandlvn.org.vn",
        list_url="https://www.congdoandlvn.org.vn/news/list",
        link_pattern=r"/news/[a-z0-9-]{20,}",
        content_selector="div.article-content, article, div.content",
        wait_for="a",
    ),

    # --- Doanh nghiệp ---
    Source(
        name="pecc1.com.vn",
        list_url="https://www.pecc1.com.vn/tin-tuc",
        link_pattern=r"/tin-tuc/[a-z0-9-]{20,}",
        content_selector="div.article-content, article, div.content",
        wait_for="a[href*='/tin-tuc/']",
        category="doanh-nghiep",
    ),
    Source(
        name="mientrungpid.com.vn",
        list_url="https://mientrungpid.com.vn/tin-tuc/tin-tuc-nganh-dien",
        link_pattern=r"/tin-tuc/tin-tuc-nganh-dien/[a-z0-9-]{15,}",
        content_selector="div.article-content, article, div.content-detail",
        wait_for="a[href*='/tin-tuc/']",
        category="doanh-nghiep",
    ),
    Source(
        name="xaylapdien.net",
        list_url="https://xaylapdien.net/tin-tuc-nganh-dien-moi-nhat",
        link_pattern=r"/[a-z0-9-]{20,}\.html",
        content_selector="div.article-content, article, div.detail",
        wait_for="a",
        category="doanh-nghiep",
    ),
    Source(
        name="nbtpc.com.vn",
        list_url="https://nbtpc.com.vn/tin-tuc",
        link_pattern=r"/tin-tuc/.+",
        content_selector="div.article-content, article, div.detail",
        wait_for="a[href*='/tin-tuc/']",
        category="doanh-nghiep",
    ),

    # --- Báo chí ---
    Source(
        name="dienvadoisong.vn",
        list_url="https://dienvadoisong.vn",
        link_pattern=r"/[a-z0-9-]{20,}-\d+\.html",
        content_selector="div.article-content, article.fck_detail, div.detail-content",
        wait_for="a",
        category="bao-chi",
    ),
    Source(
        name="nangluongsachvietnam.vn",
        list_url="https://nangluongsachvietnam.vn/c3/vi-VN/news-l/Dien-6-166",
        link_pattern=r"/d/vi-VN/news-d/[^/]+",
        content_selector="div.news-detail, article, div.content",
        wait_for="a[href*='/d/']",
        category="bao-chi",
    ),
    Source(
        name="icon.com.vn",
        list_url="https://icon.com.vn/vn/Trang-chu",
        link_pattern=r"/vn/[a-zA-Z0-9_-]{15,}",
        content_selector="div.article-content, article, div.content",
        wait_for="a[href*='/vn/']",
        category="bao-chi",
    ),
    Source(
        name="theleader.vn",
        list_url="https://theleader.vn/tieu-diem-channel387",
        link_pattern=r"/[^/]*(?:dien|nang-luong|evn|bess)[^/]*-d\d+\.html",
        content_selector="div.detail__content, article, div.content-detail",
        wait_for="a[href*='-d']",
        category="bao-chi",
    ),
]
