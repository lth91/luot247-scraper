# luot247-scraper

Playwright scraper cho 13 nguồn tin ngành điện JS-rendered (NPC, EVN HN, EVN HCM, ICON, PECC1, …) — bổ sung cho `luot247-vision/d` Edge Function `crawl-electricity-news` không xử lý được JS.


Chạy trên **Mac Mini** (`opbot@100.119.220.102` qua Tailscale), mỗi giờ phút thứ 20, giờ VN 7h-22h.

## Kiến trúc

```
MacBook (dev)  →  git push  →  GitHub  →  Mac Mini (LaunchAgent: git pull → run scraper)
                                              │
                                              └─►  Supabase REST (insert electricity_news)
```

- `scraper.py` — entry point, orchestrate flow
- `extractor.py` — Playwright Chromium load list page → extract links → fetch & parse từng bài
- `summarizer.py` — Claude Haiku tóm tắt + extract published_date
- `db.py` — Supabase REST (sb_secret_*) helpers, dedupe url_hash
- `sources.py` — 13 nguồn config: list_url, link_pattern, content_selector, wait_for
- `deploy/run.sh` — entrypoint LaunchAgent gọi: `git pull && python scraper.py`
- `deploy/com.luot247.scraper.plist` — LaunchAgent schedule

## Setup Mac Mini (chạy 1 lần)

```bash
# 1. Clone repo
mkdir -p ~/.openclaw/skills
cd ~/.openclaw/skills
git clone https://github.com/lth91/luot247-scraper.git

# 2. Python 3.11+ venv + Playwright Chromium (~300MB download)
python3 -m venv ~/.openclaw/venv-luot247
source ~/.openclaw/venv-luot247/bin/activate
pip install -r ~/.openclaw/skills/luot247-scraper/requirements.txt
playwright install chromium

# 3. Tạo .env
cp ~/.openclaw/skills/luot247-scraper/.env.example ~/.openclaw/luot247-scraper.env
# Edit: paste SUPABASE_SECRET_KEY (sb_secret_*) và ANTHROPIC_API_KEY

# 4. Apply migration (chạy 1 lần từ MacBook trong luot247-vision/)
#    cái này tạo virtual source row "Mac Mini Scraper" để gắn FK
#    cd ~/luot247-vision && supabase db push --linked

# 5. Test thủ công 1 lần
chmod +x ~/.openclaw/skills/luot247-scraper/deploy/run.sh
~/.openclaw/skills/luot247-scraper/deploy/run.sh
tail -50 ~/.openclaw/logs/luot247-scraper.log

# 6. Cài LaunchAgent (cron macOS)
cp ~/.openclaw/skills/luot247-scraper/deploy/com.luot247.scraper.plist ~/Library/LaunchAgents/
cp ~/.openclaw/skills/luot247-scraper/deploy/com.luot247.auto-pull.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.luot247.scraper.plist
launchctl load ~/Library/LaunchAgents/com.luot247.auto-pull.plist
launchctl list | grep luot247  # verify (phải thấy cả 2)

# Reload sau mỗi lần edit plist:
launchctl unload ~/Library/LaunchAgents/com.luot247.scraper.plist
launchctl load ~/Library/LaunchAgents/com.luot247.scraper.plist
```

## Deploy code mới (workflow hằng ngày)

Trên MacBook:
```bash
cd ~/luot247-scraper
# edit code
git add -A && git commit -m "..." && git push
```

Có 2 LaunchAgent chạy song song:
- `com.luot247.scraper` — chạy scraper mỗi giờ tại phút :20 (7:20→22:20 VN)
- `com.luot247.auto-pull` — check `git fetch` mỗi 5 min, nếu có commit mới
  thì pull + kickstart scraper ngay (skip nếu scraper đang chạy → đợi cycle
  kế tiếp)

→ Push code → tối đa **5 min** sau Mac Mini auto apply. Zero-touch sau
setup ban đầu. Force ngay vẫn được:

```bash
# (hiếm khi cần) force chạy ngay từ MacBook qua Tailscale:
ssh opbot@100.119.220.102 ~/.openclaw/skills/luot247-scraper/deploy/run.sh
```

Log auto-pull: `~/.openclaw/logs/auto-pull.log` — chỉ ghi khi có commit mới
(no-op khi up-to-date, không spam).

## Debug

```bash
# Live log (qua SSH)
ssh opbot@100.119.220.102 'tail -f ~/.openclaw/logs/luot247-scraper.log'

# Run thủ công không qua LaunchAgent
ssh opbot@100.119.220.102
~/.openclaw/skills/luot247-scraper/deploy/run.sh
```

## Sửa nguồn

Edit `sources.py`, push, đợi cron tiếp hoặc chạy thủ công.

Pattern match dựa trên **pathname** của URL (sau `urlparse`). Test pattern bằng:
```python
import re
re.search(r"/View/tin-tuc/.+", "/View/tin-tuc/abc-123.html")
```

## Liên quan

- Frontend đọc table `electricity_news`: https://github.com/lth91/luot247-vision
- Cùng project Supabase: `gklpvaindbfkcmuuuffz` (luot247-clone)
