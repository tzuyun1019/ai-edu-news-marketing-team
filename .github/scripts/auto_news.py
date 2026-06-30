# -*- coding: utf-8 -*-
"""
Daily EdTech AI News Auto-Updater — 完全免費版
Uses only RSS + Google Translate free web API. No API keys needed.
"""
import os, re, json, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    os.system("pip install feedparser -q")
    import feedparser

TPE = timezone(timedelta(hours=8))
HTML_FILE = 'index.html'
DOW_ZH = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']

RSS_FEEDS = [
    ("EdSurge",          "https://edsurge.com/news.rss"),
    ("eSchool News AI",  "https://www.eschoolnews.com/category/artificial-intelligence/feed/"),
    ("eSchool News",     "https://www.eschoolnews.com/feed/"),
    ("EdTech Magazine",  "https://edtechmagazine.com/k12/rss.xml"),
    ("TechCrunch Edu",   "https://techcrunch.com/category/education/feed/"),
    ("Getting Smart",    "https://www.gettingsmart.com/feed/"),
    ("eLearning Ind.",   "https://elearningindustry.com/feed"),
    ("ISTE",             "https://www.iste.org/rss.xml"),
]

AI_KEYWORDS = [
    'ai ', ' ai,', 'artificial intelligence', 'machine learning',
    'chatgpt', 'gpt', 'claude', 'gemini', 'copilot', 'llm',
    'generative', 'edtech', 'ed tech', 'learning technology',
    'personalized learning', 'adaptive learning', 'tutor', 'chatbot',
    'automation', 'deep learning', 'language model',
]

SECTION_MAP = {
    'funding': ('資金動態', 'tag-funding'),
    'invest':  ('資金動態', 'tag-funding'),
    'raise':   ('資金動態', 'tag-funding'),
    'partner': ('機構合作', 'tag-partner'),
    'school':  ('機構合作', 'tag-partner'),
    'universit': ('機構合作', 'tag-partner'),
    'research': ('效果研究', 'tag-research'),
    'study':   ('效果研究', 'tag-research'),
    'outcome': ('效果研究', 'tag-research'),
    'taiwan':  ('台灣與亞洲', 'tag-taiwan'),
    'asia':    ('台灣與亞洲', 'tag-taiwan'),
    'japan':   ('台灣與亞洲', 'tag-taiwan'),
    'korea':   ('台灣與亞洲', 'tag-taiwan'),
    'singapore': ('台灣與亞洲', 'tag-taiwan'),
    'china':   ('台灣與亞洲', 'tag-taiwan'),
    'trend':   ('市場趨勢', 'tag-market'),
    'market':  ('市場趨勢', 'tag-market'),
    'report':  ('市場趨勢', 'tag-market'),
}

def guess_section(title, summary):
    text = (title + ' ' + summary).lower()
    for kw, (sec, tag) in SECTION_MAP.items():
        if kw in text:
            return sec, tag
    return '產品動態', 'tag-product'

TAG_LABEL = {
    'tag-product': '產品', 'tag-funding': '資金',
    'tag-partner': '合作', 'tag-research': '研究',
    'tag-market': '趨勢', 'tag-taiwan': '台灣',
}


# ── Google Translate (free web, no key) ──────────────────────────────────────

def gtranslate(text, target='zh-TW'):
    """Translate text using Google Translate web (free, no API key)."""
    if not text or not text.strip():
        return text
    text = text[:500]
    url = "https://translate.googleapis.com/translate_a/single"
    params = urllib.parse.urlencode({
        'client': 'gtx', 'sl': 'auto', 'tl': target,
        'dt': 't', 'q': text
    })
    req = urllib.request.Request(
        f"{url}?{params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
            parts = [seg[0] for seg in data[0] if seg[0]]
            return ''.join(parts)
    except Exception as e:
        print(f"  Translate error: {e}")
        return text  # Return English as fallback


def translate_batch(items, field, target='zh-TW', delay=0.3):
    """Translate a field for a list of dicts, with rate-limit delay."""
    for item in items:
        item[field + '_zh'] = gtranslate(item[field], target)
        time.sleep(delay)
    return items


# ── RSS fetching ──────────────────────────────────────────────────────────────

def strip_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def is_ai_edu(title, summary):
    text = (title + ' ' + (summary or '')).lower()
    return any(kw in text for kw in AI_KEYWORDS)

def fetch_entries(max_age_hours=72):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    entries = []
    seen = set()

    for source_name, url in RSS_FEEDS:
        try:
            print(f"  {source_name}…")
            feed = feedparser.parse(url)
            for e in feed.entries[:20]:
                if hasattr(e, 'published_parsed') and e.published_parsed:
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    if pub < cutoff:
                        continue
                link = e.get('link', '')
                if link in seen:
                    continue
                title = e.get('title', '').strip()
                summary = strip_html(e.get('summary', ''))[:400]
                if title and is_ai_edu(title, summary):
                    seen.add(link)
                    entries.append({
                        'title': title,
                        'summary': summary[:200],
                        'url': link,
                        'source': source_name,
                    })
        except Exception as ex:
            print(f"  Error {source_name}: {ex}")

    print(f"  {len(entries)} entries found")
    return entries[:12]


# ── Story building ────────────────────────────────────────────────────────────

def make_takeaway_zh(section):
    takeaway_map = {
        '資金動態': '台灣 EdTech 廠商可關注此輪融資背後的商業模式，評估類似市場切入點的機會。',
        '機構合作': '台灣學校與 EdTech 廠商可參考此合作模式，探索在地化合作可能性。',
        '效果研究': '此研究數據可作為向學校推銷 AI 教育工具時的佐證，建議整理成投影片素材。',
        '台灣與亞洲': '亞洲市場動態與台灣高度相關，可作為行銷策略參考，尤其是定價與推廣節奏。',
        '市場趨勢': '此趨勢可用於對客戶說明市場方向，強化 AI 教育工具採購的決策信心。',
        '產品動態': '行銷團隊可追蹤此工具的用戶反饋，作為比較競品或合作機會的評估依據。',
    }
    return takeaway_map.get(section, '建議行銷團隊持續追蹤此動態，並評估對台灣教育市場的影響。')

def build_stories(entries):
    stories = []
    for e in entries[:8]:
        section, tag_class = guess_section(e['title'], e['summary'])
        title_zh = gtranslate(e['title'])
        time.sleep(0.4)
        summary_zh = gtranslate(e['summary'][:200])
        time.sleep(0.4)

        # para1 = translated summary (facts)
        # para2 = short significance note
        para2_map = {
            '資金動態': f"此次融資顯示投資人持續看好 AI 教育市場潛力，資金流向具有方向性參考價值。",
            '機構合作': f"大型機構採用 AI 教育工具的案例，有助於降低其他機構的採購決策門檻。",
            '效果研究': f"有效果數據支持的 AI 教育工具更容易獲得學校採購信任，市場說服力提升。",
            '台灣與亞洲': f"亞洲 EdTech 市場發展與台灣高度連動，值得行銷團隊持續追蹤。",
            '市場趨勢': f"市場趨勢清楚顯示 AI 在教育場景的滲透持續加速，競爭格局正在改變。",
            '產品動態': f"新工具或功能的推出代表市場競爭加劇，行銷策略需要相應調整。",
        }

        stories.append({
            'section': section,
            'tagClass': tag_class,
            'title': title_zh,
            'para1': summary_zh,
            'para2': para2_map.get(section, '此動態值得行銷團隊持續關注，有助於掌握 AI 教育工具市場走向。'),
            'takeaway': make_takeaway_zh(section),
            'sourceUrl': e['url'],
            'sourceName': e['source'],
        })
    return stories


# ── HTML building & modification (same as before) ────────────────────────────

def date_str(dt):    return dt.strftime('%Y-%m-%d')
def month_day(ds):
    m, d = str(int(ds[5:7])), str(int(ds[8:10]))
    return f'{m}/{d}'

def build_story_item(story):
    data = json.dumps(story, ensure_ascii=False).replace("'", "&#39;")
    tag_label = TAG_LABEL.get(story['tagClass'], '趨勢')
    source_short = story['sourceName'].split(' · ')[0]
    return f"""      <div class="news-item" onclick="selectNews(this)"
        data-story='{data}'>
        <span class="tag {story['tagClass']}">{tag_label}</span>
        <div class="item-text">
          <div class="item-title">{story['title']}</div>
          <div class="item-source">{source_short}</div>
        </div>
      </div>"""

def build_day_pane(day_str, stories):
    dt = datetime.strptime(day_str, '%Y-%m-%d')
    dow = DOW_ZH[dt.weekday()]
    m_str = str(int(day_str[5:7]))
    d_str = str(int(day_str[8:10]))

    grouped = {}
    order = []
    for s in stories:
        sec = s['section']
        if sec not in grouped:
            grouped[sec] = []
            order.append(sec)
        grouped[sec].append(s)

    body_lines = []
    for sec in order:
        body_lines.append(f'      <div class="section-label">{sec}</div>')
        for story in grouped[sec]:
            body_lines.append(build_story_item(story))

    return f"""<section class="day-pane" data-day="{day_str}">
  <div class="split">
    <aside class="news-list" id="list-{day_str}">
      <div class="pane-header">{m_str}月{d_str}日（{dow}）<span class="count"> · {len(stories)} 則</span></div>

{chr(10).join(body_lines)}

    </aside>
    <div class="detail-panel" id="detail-{day_str}">
      <div class="detail-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        <p>點擊左側新聞查看詳情</p>
      </div>
    </div>
  </div>
</section>"""

def make_tab(cls, week, ds):
    dt = datetime.strptime(ds, '%Y-%m-%d')
    dow = DOW_ZH[dt.weekday()]
    md = month_day(ds)
    today_span = '<span class="tab-today">今日</span>' if 'active' in cls else ''
    return f'  <button class="{cls}" data-week="{week}" data-day="{ds}"><span class="tab-dow">{dow}</span><span class="tab-date">{md}</span>{today_span}</button>'

def apply_daily_append(html, today_str, yesterday_str, new_pane):
    # Yesterday tab: remove active + tab-today
    html = re.sub(
        rf'<button class="tab active" (data-week="[01]" data-day="{yesterday_str}")>(<span[^<]*</span><span[^<]*</span>)<span class="tab-today">今日</span></button>',
        r'<button class="tab" \1>\2</button>', html)
    # Today tab: empty → active + today
    html = re.sub(
        rf'<button class="tab empty" (data-week="0" data-day="{today_str}")>(<span[^<]*</span><span[^<]*</span>)</button>',
        r'<button class="tab active" \1>\2<span class="tab-today">今日</span></button>', html)
    # All panes → add hidden
    def add_hidden(m):
        tag, inner = m.group(1), m.group(2)
        if 'hidden' not in tag:
            tag = tag.rstrip('>') + ' hidden>'
        return tag + inner + '</section>'
    html = re.sub(r'(<section[^>]+class="day-pane"[^>]*>)([\s\S]*?)</section>', add_hidden, html)
    # Insert new pane
    html = re.sub(r'(<section[^>]+class="day-pane")', new_pane + '\n\n      \\1', html, count=1)
    return html

def apply_monday_reset(html, today_str, new_pane):
    today_dt = datetime.strptime(today_str, '%Y-%m-%d')
    cutoff_dt = today_dt - timedelta(days=14)
    # Delete week-1 tabs
    html = re.sub(r'\s*<button[^>]+data-week="1"[^>]*>[\s\S]*?</button>', '', html)
    # Demote week-0 to week-1
    def demote(m):
        t = m.group(0).replace('data-week="0"', 'data-week="1"')
        t = re.sub(r'class="tab [^"]*"', 'class="tab"', t)
        return re.sub(r'<span class="tab-today">今日</span>', '', t)
    html = re.sub(r'<button[^>]+data-week="0"[^>]*>[\s\S]*?</button>', demote, html)
    # New week-0 tabs
    tabs = [make_tab('tab active' if i == 0 else 'tab empty', '0',
                     date_str(today_dt + timedelta(days=i))) for i in range(7)]
    html = re.sub(r'(<nav class="day-tabs"[^>]*>\s*)', r'\1' + '\n'.join(tabs) + '\n      ', html, count=1)
    # Delete old panes
    def keep_pane(m):
        ds = re.search(r'data-day="([^"]+)"', m.group(0))
        if ds and datetime.strptime(ds.group(1), '%Y-%m-%d') < cutoff_dt:
            return ''
        return m.group(0)
    html = re.sub(r'<section[^>]+class="day-pane"[\s\S]*?</section>', keep_pane, html)
    # Add hidden to remaining
    def add_hidden(m):
        tag, inner = m.group(1), m.group(2)
        if 'hidden' not in tag:
            tag = tag.rstrip('>') + ' hidden>'
        return tag + inner + '</section>'
    html = re.sub(r'(<section[^>]+class="day-pane"[^>]*>)([\s\S]*?)</section>', add_hidden, html)
    # Insert new pane
    html = re.sub(r'(<section[^>]+class="day-pane")', new_pane + '\n\n      \\1', html, count=1)
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(TPE)
    today_str = date_str(now)
    yesterday_str = date_str(now - timedelta(days=1))
    is_monday = now.weekday() == 0

    print(f"📅 {today_str} ({'週一 RESET' if is_monday else DOW_ZH[now.weekday()]})")

    print("\n🔍 Fetching RSS…")
    entries = fetch_entries(72)
    if len(entries) < 3:
        print("Expanding to 120h…")
        entries = fetch_entries(120)
    if not entries:
        raise RuntimeError("No entries — aborting")

    print(f"\n🌐 Translating {len(entries[:8])} stories…")
    stories = build_stories(entries)

    if len(stories) < 4:
        raise RuntimeError(f"Only {len(stories)} stories — aborting")

    new_pane = build_day_pane(today_str, stories)

    print(f"\n📄 Reading {HTML_FILE}…")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    print(f"✏️  {'Monday reset' if is_monday else 'Daily append'}…")
    if is_monday:
        html = apply_monday_reset(html, today_str, new_pane)
    else:
        html = apply_daily_append(html, today_str, yesterday_str, new_pane)

    ts = now.strftime('%Y-%m-%d %H:%M (Asia/Taipei)')
    html = re.sub(r'<span id="updated">[^<]*</span>', f'<span id="updated">{ts}</span>', html)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Done! {len(stories)} stories, timestamp: {ts}")

if __name__ == '__main__':
    main()
