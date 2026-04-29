# Emergency Cheat Sheet — luot247 /d

Mở file này từ GitHub mobile app khi anh đi xa và có sự cố.

## Quick Links

- **Supabase SQL Editor**: https://supabase.com/dashboard/project/gklpvaindbfkcmuuuffz/editor
- **Supabase Edge Functions**: https://supabase.com/dashboard/project/gklpvaindbfkcmuuuffz/functions
- **Anthropic billing**: https://console.anthropic.com/settings/billing
- **Vercel dashboard**: https://vercel.com/dashboard
- **Frontend**: https://www.luot247.com/d

## Health check (chạy đầu tiên khi nghi sự cố)

Mở Supabase SQL Editor, paste và chạy:

```sql
-- 1. Articles ingest rate (24h, 7d)
SELECT
  count(*) FILTER (WHERE crawled_at > now() - interval '1 hour') as h1,
  count(*) FILTER (WHERE crawled_at > now() - interval '24 hours') as d1,
  count(*) FILTER (WHERE crawled_at > now() - interval '7 days') as w1,
  count(*) as total
FROM electricity_news;
-- Bình thường: h1 >= 1, d1 >= 30, w1 >= 150
-- Nếu d1 < 10 → có vấn đề.

-- 2. Cron jobs status (last 12 runs)
SELECT jobname, start_time, status, return_message
FROM cron_recent_runs
ORDER BY start_time DESC
LIMIT 12;
-- Bình thường: tất cả status='succeeded'.

-- 3. Sources với failures
SELECT name, is_active, consecutive_failures, last_crawled_at
FROM electricity_sources
WHERE consecutive_failures > 0 OR last_crawled_at < now() - interval '6 hours'
ORDER BY consecutive_failures DESC;
```

## Common Issues + Fixes

### Bài lỗi (date sai, content sai, off-topic)

```sql
-- Tìm bài
SELECT id, title, published_at, source_name, original_url
FROM electricity_news
WHERE title ILIKE '%KEYWORD%'
ORDER BY crawled_at DESC LIMIT 10;

-- Xóa
DELETE FROM electricity_news WHERE id = 'PASTE-UUID-HERE';
```

### Một nguồn Mac Mini Scraper spam bài rác

```sql
-- Tạm dừng toàn bộ Mac Mini Scraper (insert sẽ fail FK):
UPDATE electricity_sources SET is_active = false WHERE name = 'Mac Mini Scraper';

-- Bật lại sau:
UPDATE electricity_sources SET is_active = true WHERE name = 'Mac Mini Scraper';
```

### Một nguồn edge function (HTTP scraper) spam / lỗi

```sql
-- Tìm tên nguồn:
SELECT name, is_active FROM electricity_sources WHERE name ILIKE '%KEYWORD%';

-- Disable:
UPDATE electricity_sources SET is_active = false WHERE name = 'TÊN NGUỒN';

-- Reset failures + enable:
UPDATE electricity_sources SET consecutive_failures = 0, is_active = true WHERE name = 'TÊN NGUỒN';
```

### Edge function fail liên tục (cron status='failed')

Vào Supabase Edge Functions → click function (ví dụ `crawl-electricity-news`) → tab **Logs** → xem error.

Phổ biến:
- **Anthropic 401**: API key sai/hết hạn → vào console.anthropic.com tạo key mới → vào Supabase → Settings → Edge Function Secrets → update `ANTHROPIC_API_KEY`
- **Anthropic 429**: rate limit / hết credit → check billing
- **Site 403/timeout**: nguồn block → consecutive_failures sẽ tự auto-disable sau 5 lần

### Frontend trắng / 500 error

- Mở Vercel dashboard → project luot247-vision → Deployments
- Nếu có deployment FAILED → rollback về deployment trước đó (button **...** → Promote)

### Mac Mini scraper im (không insert bài Mac Mini suốt 2-3 giờ)

Có thể Mac Mini bị mất điện hoặc Tailscale offline. Không cần ssh — chờ về sửa.

Workaround tạm: edge function vẫn chạy 23 nguồn HTTP khác → vẫn có ~30 bài/24h từ các nguồn đó.

## Code edit từ mobile (GitHub app)

1. Mở GitHub app → repo `lth91/luot247-scraper` (cho scraper) hoặc `lth91/luot247-vision` (cho frontend)
2. Tìm file → tap icon ✏️ → sửa → Commit changes (commit trực tiếp lên main)
3. **Frontend (luot247-vision)**: Vercel tự deploy sau ~1 phút
4. **Scraper (luot247-scraper)**: Mac Mini tự `git pull` ở lần LaunchAgent fire kế tiếp (max 1h)

## Architecture nhắc nhanh

```
Frontend www.luot247.com (Vercel) ── đọc ──► Supabase electricity_news table
                                              ▲
                                              │ insert
                  ┌───────────────────────────┼───────────────────────────┐
                  │                           │                           │
       Edge functions (mỗi giờ)       Mac Mini scraper                  RSS
       crawl-electricity-news         (Playwright, mỗi giờ HH:20)
       discovery-rss-news             12 nguồn JS-rendered
       23 nguồn HTTP/RSS              (icon, evnhcmc, evnhanoi, …)
```

Edge functions chạy **độc lập** với Mac Mini. Nếu Mac Mini chết, edge functions vẫn ingest đều.

## Threshold báo động

| Metric | OK | Cần lo |
|--------|-----|--------|
| Bài/24h | ≥ 30 | < 10 |
| Cron job failed liên tiếp | 0-1 | ≥ 3 |
| Anthropic credit | > $10 | < $2 |
| consecutive_failures sources | < 5 | ≥ 5 (auto-disable) |
