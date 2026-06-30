# -*- coding: utf-8 -*-
"""
Daily EdTech AI News Auto-Updater
Runs in GitHub Actions. Reads index.html, fetches RSS, calls Claude Haiku,
writes back updated index.html with today's news.
"""
import os, re, json, urllib.request
from datetime import datetime, timezone, timedelta

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
TPE = timezone(timedelta(hours=8))
HTML_FILE = 'index.html'

DOW_ZH = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']

RSS_FEEDS = [
    ("EdSurge",          "https://edsurge.com/news.rss"),
    ("eSchool News",     "https://www.eschoolnews.com/feed/"),
    ("EdTech Magazine",  "https://edtechmagazine.com/k12/rss.xml"),
    ("TechCrunch Edu",   "https://techcrunch.com/category/education/feed/"),
    ("Getting Smart",    "https://www.gettingsmart.com/feed/"),
    ("eLearning Ind.",   "https://elearningindustry.com/feed"),
]

AI_KEYWORDS = [
    'ai ', ' ai', 'artificial intelligence', 'machine learning',
    'chatgpt', 'gpt', 'claude', 'gemini', 'copilot', 'llm',
    'generative', 'edtech', 'ed tech', 'learning technology',
    'personalized learning', 'adaptive learning', 'tutor', 'chatbot',
    'automation', 'robot', 'neural', 'deep learning',
]


# ── Date helpers ────────────────────────────────────────────────────────────

def today_taipei():
    return datetime.now(TPE)

def date_str(dt):
    return dt.strftime('%Y-%m-%d')

def month_day(ds):
    """'2026-06-30' → '6/30'"""
    m, d = str(int(ds[5:7])), str(int(ds[8:10]))
    return f'{m}/{d}'

def week_monday(dt):
    """Return the Monday of dt's week."""
    return dt - timedelta(days=dt.weekday())


# ── RSS fetching ─────────────────────────────────────────────────────────────

def is_ai_edu(title, summary):
    text = (title + ' ' + (summary or '')).lower()
    return any(kw in text for kw in AI_KEYWORDS)

def strip_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def fetch_rss_entries(max_age_hours=72):
    try:
        import feedparser
    except ImportError:
        print("feedparser not installed, skipping RSS fetch")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    entries = []
    seen_urls = set()

    for source_name, url in RSS_FEEDS:
        try:
            print(f"  Fetching {source_name}…")
            feed = feedparser.parse(url)
            for e in feed.entries[:25]:
                if hasattr(e, 'published_parsed') and e.published_parsed:
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    if pub < cutoff:
                        continue
                link = e.get('link', '')
                if link in seen_urls:
                    continue
                title = e.get('title', '').strip()
                summary = strip_html(e.get('summary', ''))[:400]
                if title and is_ai_edu(title, summary):
                    seen_urls.add(link)
                    entries.append({
                        'title': title,
                        'summary': summary,
                        'url': link,
                        'source': source_name,
                    })
        except Exception as ex:
            print(f"  Error {source_name}: {ex}")

    print(f"  Found {len(entries)} AI/EdTech entries")
    return entries


# ── Claude Haiku call ─────────────────────────────────────────────────────────

def generate_stories(entries):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    if not entries:
        raise RuntimeError("No RSS entries to process")

    news_list = "\n".join([
        f"{i+1}. [{e['source']}] {e['title']}\n   URL: {e['url']}\n   摘要: {e['summary'][:250]}"
        for i, e in enumerate(entries[:15])
    ])

    prompt = f"""你是台灣行銷團隊的AI教育情報分析師，閱讀者是教育科技業的行銷人員。

以下是今日EdTech AI新聞，請挑選最值得關注的8則（分類多元，優先選AI工具/產品，再選市場趨勢），為每則生成繁體中文內容。

輸出純 JSON 陣列（不要 markdown，不要說明文字），每個物件包含：
- source_index: 原始編號（1-based integer）
- section: 分類（產品動態 / 工具推薦 / 資金動態 / 市場趨勢 / 台灣與亞洲）
- tagClass: CSS class（tag-product / tag-funding / tag-partner / tag-research / tag-market / tag-taiwan）
- title: 標題（15-30字，有洞察力，從台灣行銷角度出發）
- para1: 事實與背景（60-80字）
- para2: 重點意義與影響（50-70字）
- takeaway: 台灣行銷團隊可操作建議（50-80字，第一人稱複數）
- sourceName: 媒體名稱（如 "EdSurge · 文章標題前10字"）

注意：sourceUrl 不用輸出（我從 source_index 對應原始 URL）

新聞清單：
{news_list}"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)

    text = data['content'][0]['text'].strip()
    # Extract JSON array even if wrapped in ```
    m = re.search(r'\[[\s\S]*\]', text)
    if not m:
        raise RuntimeError(f"No JSON array in Haiku response: {text[:300]}")
    stories = json.loads(m.group())

    # Attach sourceUrl from original entries
    for s in stories:
        idx = s.get('source_index', 1) - 1
        if 0 <= idx < len(entries):
            s['sourceUrl'] = entries[idx]['url']
        else:
            s['sourceUrl'] = ''

    print(f"  Haiku generated {len(stories)} stories")
    return stories


# ── HTML generation ───────────────────────────────────────────────────────────

def build_story_item(story):
    section   = story.get('section', '市場趨勢')
    tag_class = story.get('tagClass', 'tag-market')
    title     = story['title']
    para1     = story.get('para1', '')
    para2     = story.get('para2', '')
    takeaway  = story.get('takeaway', '')
    source_url = story.get('sourceUrl', '#')
    source_name = story.get('sourceName', '')

    # Escape single quotes in data-story JSON value
    data = json.dumps({
        "section": section,
        "tagClass": tag_class,
        "title": title,
        "para1": para1,
        "para2": para2,
        "takeaway": takeaway,
        "sourceUrl": source_url,
        "sourceName": source_name,
    }, ensure_ascii=False).replace("'", "&#39;")

    tag_labels = {
        'tag-product': '產品', 'tag-funding': '資金',
        'tag-partner': '合作', 'tag-research': '研究',
        'tag-market': '趨勢', 'tag-taiwan': '台灣',
    }
    tag_label = tag_labels.get(tag_class, '趨勢')

    return f"""      <div class="news-item" onclick="selectNews(this)"
        data-story='{data}'>
        <span class="tag {tag_class}">{tag_label}</span>
        <div class="item-text">
          <div class="item-title">{title}</div>
          <div class="item-source">{source_name.split(' · ')[0] if ' · ' in source_name else source_name}</div>
        </div>
      </div>"""


def build_day_pane(day_str, stories):
    """Build the complete <section class="day-pane"> for one day."""
    dt = datetime.strptime(day_str, '%Y-%m-%d')
    dow = DOW_ZH[dt.weekday()]
    md = month_day(day_str)
    count = len(stories)

    # Group by section
    sections = []
    seen_sections = []
    grouped = {}
    for s in stories:
        sec = s.get('section', '市場趨勢')
        if sec not in grouped:
            grouped[sec] = []
            seen_sections.append(sec)
        grouped[sec].append(s)

    body_lines = []
    for sec in seen_sections:
        body_lines.append(f'      <div class="section-label">{sec}</div>')
        for story in grouped[sec]:
            body_lines.append(build_story_item(story))

    body = '\n'.join(body_lines)

    return f"""<section class="day-pane" data-day="{day_str}">
  <div class="split">
    <aside class="news-list" id="list-{day_str}">
      <div class="pane-header">{md[0] if md[0].isdigit() else md}月{md.split('/')[1]}日（{dow}）<span class="count"> · {count} 則</span></div>

{body}

    </aside>
    <div class="detail-panel" id="detail-{day_str}">
      <div class="detail-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        <p>點擊左側新聞查看詳情</p>
      </div>
    </div>
  </div>
</section>"""


def make_tab(cls, week, day_str):
    dt = datetime.strptime(day_str, '%Y-%m-%d')
    dow = DOW_ZH[dt.weekday()]
    md = month_day(day_str)
    today_span = '<span class="tab-today">今日</span>' if 'active' in cls else ''
    return f'  <button class="{cls}" data-week="{week}" data-day="{day_str}"><span class="tab-dow">{dow}</span><span class="tab-date">{md}</span>{today_span}</button>'


# ── HTML modification: daily append (non-Monday) ──────────────────────────────

def apply_daily_append(html, today_str, yesterday_str, new_pane_html):
    """
    Non-Monday logic:
    1. Yesterday's active tab → tab (remove active + tab-today)
    2. Today's empty tab → tab active (add tab-today)
    3. All existing day-panes → add hidden
    4. Insert new day-pane at top
    """
    # 1. Yesterday: remove active + tab-today span
    html = re.sub(
        rf'(<button class="tab active" data-week="0" data-day="{yesterday_str}">)([\s\S]*?)(<span class="tab-today">今日</span>)',
        lambda m: m.group(1).replace('tab active', 'tab') + m.group(2),
        html, count=1
    )
    # Also handle case where yesterday is data-week="1"
    html = re.sub(
        rf'(<button class="tab active" data-week="1" data-day="{yesterday_str}">)([\s\S]*?)(<span class="tab-today">今日</span>)',
        lambda m: m.group(1).replace('tab active', 'tab') + m.group(2),
        html, count=1
    )

    # 2. Today: empty → active + tab-today
    html = re.sub(
        rf'<button class="tab empty" data-week="0" data-day="{today_str}">(<span class="tab-dow">[^<]*</span><span class="tab-date">[^<]*</span>)</button>',
        rf'<button class="tab active" data-week="0" data-day="{today_str}">\1<span class="tab-today">今日</span></button>',
        html, count=1
    )

    # 3. All existing panes → add hidden
    def add_hidden(m):
        tag = m.group(1)
        inner = m.group(2)
        if 'hidden' not in tag:
            tag = tag.rstrip('>') + ' hidden>'
        return tag + inner + '</section>'
    html = re.sub(r'(<section[^>]+class="day-pane"[^>]*>)([\s\S]*?)</section>', add_hidden, html)

    # 4. Insert new pane before the first existing <section class="day-pane"
    html = re.sub(r'(<section[^>]+class="day-pane")',
                  new_pane_html + '\n\n      \\1', html, count=1)

    return html


# ── HTML modification: Monday reset ──────────────────────────────────────────

def apply_monday_reset(html, today_str, new_pane_html):
    """
    Monday logic:
    1. Delete all data-week="1" tabs
    2. Change data-week="0" tabs → data-week="1"
    3. Insert 7 new data-week="0" tabs (Mon=today active, rest empty)
    4. Delete panes older than 14 days
    5. Insert new day-pane at top
    """
    today_dt = datetime.strptime(today_str, '%Y-%m-%d')
    cutoff_dt = today_dt - timedelta(days=14)

    # 1. Delete week-1 tabs
    html = re.sub(r'\s*<button[^>]+data-week="1"[^>]*>[\s\S]*?</button>', '', html)

    # 2. Change week-0 to week-1 (and remove active/tab-today from old tabs)
    def demote_tab(m):
        tag = m.group(0)
        tag = tag.replace('data-week="0"', 'data-week="1"')
        tag = re.sub(r' active', '', tag)
        tag = re.sub(r'<span class="tab-today">今日</span>', '', tag)
        return tag
    html = re.sub(r'<button[^>]+data-week="0"[^>]*>[\s\S]*?</button>', demote_tab, html)

    # 3. Build 7 new week-0 tabs (today=Monday=active, rest=empty)
    new_tabs = []
    for i in range(7):
        d = today_dt + timedelta(days=i)
        ds = date_str(d)
        cls = 'tab active' if i == 0 else 'tab empty'
        new_tabs.append(make_tab(cls, '0', ds))
    new_tabs_html = '\n'.join(new_tabs)

    # Insert before first data-week="1" tab in nav
    html = re.sub(
        r'(<nav class="day-tabs"[^>]*>\s*)',
        r'\1' + new_tabs_html + '\n      ',
        html, count=1
    )

    # 4. Delete panes older than 14 days
    def keep_pane(m):
        ds = re.search(r'data-day="([^"]+)"', m.group(0))
        if ds:
            pane_dt = datetime.strptime(ds.group(1), '%Y-%m-%d')
            if pane_dt < cutoff_dt:
                return ''
        return m.group(0)
    html = re.sub(r'<section[^>]+class="day-pane"[\s\S]*?</section>', keep_pane, html)

    # 5. Add hidden to all remaining panes
    def add_hidden(m):
        tag = m.group(1); inner = m.group(2)
        if 'hidden' not in tag:
            tag = tag.rstrip('>') + ' hidden>'
        return tag + inner + '</section>'
    html = re.sub(r'(<section[^>]+class="day-pane"[^>]*>)([\s\S]*?)</section>', add_hidden, html)

    # 6. Insert new pane at top
    html = re.sub(r'(<section[^>]+class="day-pane")',
                  new_pane_html + '\n\n      \\1', html, count=1)

    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now = today_taipei()
    today_str = date_str(now)
    yesterday_str = date_str(now - timedelta(days=1))
    is_monday = now.weekday() == 0

    print(f"📅 Today: {today_str} ({'週一 RESET' if is_monday else DOW_ZH[now.weekday()]})")

    # Fetch news
    print("\n🔍 Fetching RSS feeds…")
    entries = fetch_rss_entries(max_age_hours=72)

    if len(entries) < 3:
        print("⚠️  Too few entries, expanding to 120h")
        entries = fetch_rss_entries(max_age_hours=120)

    if not entries:
        raise RuntimeError("No RSS entries found — aborting")

    # Generate Chinese content
    print("\n🤖 Calling Claude Haiku…")
    stories = generate_stories(entries)

    if len(stories) < 6:
        raise RuntimeError(f"Only {len(stories)} stories generated — aborting")

    # Build day-pane HTML
    new_pane = build_day_pane(today_str, stories)

    # Read current index.html
    print(f"\n📄 Reading {HTML_FILE}…")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # Apply changes
    print(f"\n✏️  Applying {'Monday reset' if is_monday else 'daily append'}…")
    if is_monday:
        html = apply_monday_reset(html, today_str, new_pane)
    else:
        html = apply_daily_append(html, today_str, yesterday_str, new_pane)

    # Update footer timestamp
    ts = now.strftime('%Y-%m-%d %H:%M (Asia/Taipei)')
    html = re.sub(r'<span id="updated">[^<]*</span>', f'<span id="updated">{ts}</span>', html)

    # Write back
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Done! {len(stories)} stories written to {HTML_FILE}")
    print(f"   Timestamp: {ts}")


if __name__ == '__main__':
    main()
