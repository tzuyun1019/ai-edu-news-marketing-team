import json, re, os, sys
from datetime import datetime, timezone, timedelta

LINE_TOKEN = os.environ["LINE_TOKEN_QUICK"]
SITE_URL = "https://tzuyun1019.github.io/ai-edu-news-marketing-team/"

TPE = timezone(timedelta(hours=8))
now = datetime.now(TPE)
UPDATE_TIME = now.strftime("%Y-%m-%d %H:%M (Asia/Taipei)")
print(f"台北時間: {now.strftime('%Y-%m-%d %H:%M')}")

# 直接讀本地 checkout 的 index.html（比 raw.githubusercontent.com 更快更穩）
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()
print("index.html 讀取成功")

pane_matches = re.findall(
    r'<section[^>]+class="day-pane"[^>]+data-day="(\d{4}-\d{2}-\d{2})"[^>]*>([\s\S]*?)(?=<section[^>]+class="day-pane"|<div id="emptyPane")',
    html
)
if not pane_matches:
    print("找不到任何 day-pane")
    sys.exit(1)

pane_matches.sort(key=lambda x: x[0], reverse=True)
latest_date, latest_pane = pane_matches[0]
print(f"使用日期: {latest_date}")

dt = datetime.strptime(latest_date, "%Y-%m-%d")
zh_week = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
DATE_STR = f"{dt.year}年{dt.month}月{dt.day}日（{zh_week[dt.weekday()]}）"

stories_raw = re.findall(r"data-story='([^']+)'", latest_pane)
stories = []
for s in stories_raw:
    try:
        d = json.loads(s)
        para1 = d.get("para1", "")
        summary = para1[:45] + "…" if len(para1) > 45 else para1
        stories.append({"section": d["section"], "title": d["title"], "summary": summary})
    except:
        pass

if not stories:
    print("沒有解析到 story")
    sys.exit(1)
print(f"共 {len(stories)} 則")

def make_story_box(story, is_last):
    items = [
        {"type": "text", "text": story["title"], "weight": "bold", "size": "sm", "color": "#5C4A3D", "wrap": True},
        {"type": "text", "text": story["summary"], "size": "xs", "color": "#8B7355", "wrap": True, "margin": "xs"}
    ]
    box = {"type": "box", "layout": "vertical", "spacing": "xs", "contents": items}
    if not is_last:
        return [box, {"type": "separator", "color": "#D4C5B0", "margin": "sm"}]
    return [box]

def section_label(name):
    return {"type": "text", "text": name, "size": "xs", "weight": "bold", "color": "#7A8F7A", "margin": "md"}

body_contents = []
current_section = None
for i, s in enumerate(stories):
    if s["section"] != current_section:
        current_section = s["section"]
        body_contents.append(section_label(current_section))
    body_contents.extend(make_story_box(s, i == len(stories) - 1))

flex_msg = {
    "type": "flex",
    "altText": f"📰 教育AI快讀 {DATE_STR} · 共{len(stories)}則",
    "contents": {
        "type": "bubble", "size": "giga",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#9CAF8B", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📰 教育 AI 快讀情報", "color": "#FFFFFF", "size": "lg", "weight": "bold"},
                {"type": "text", "text": f"{DATE_STR}　·　共 {len(stories)} 則", "color": "#E0EDD8", "size": "sm", "margin": "xs"},
                {"type": "text", "text": f"🕐 {UPDATE_TIME}", "color": "#C5D9BA", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "backgroundColor": "#F5F0EB",
            "spacing": "sm", "paddingAll": "14px", "contents": body_contents
        },
        "footer": {
            "type": "box", "layout": "vertical", "backgroundColor": "#F5F0EB", "paddingAll": "12px",
            "contents": [{"type": "button", "action": {"type": "uri", "label": "開啟快讀版 →", "uri": SITE_URL},
                          "style": "primary", "color": "#8BA3B4", "height": "sm"}]
        }
    }
}

import urllib.request
payload = json.dumps({"messages": [flex_msg]}).encode()
req = urllib.request.Request(
    "https://api.line.me/v2/bot/message/broadcast",
    data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"✅ LINE 廣播成功！{len(stories)} 則，所有好友都已收到。Status: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"❌ LINE 廣播失敗：HTTP {e.code}")
    print(e.read().decode())
    sys.exit(1)
