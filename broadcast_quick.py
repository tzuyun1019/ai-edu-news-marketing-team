import json, urllib.request, os, sys

LINE_TOKEN = "xWvZIRxhfUq17uj/JsOtz+RWuMbJFbtis4t6mkO8V+FQYyc5W32kulfiaHh/ZGd+t3G3lS4Ow+T0ukQcg/nrS7a1MtbcPIVcdepclJjRDssMR8gasxaeYloPnhzZWwdbGMSJ+HRb1e86DDqGrsW1iQdB04t89/1O/w1cDnyilFU="
SITE_URL = "https://tzuyun1019.github.io/ai-edu-news-marketing-team/"
FLAG_FILE = "/tmp/broadcast_done_today"

# ★ 防止重複廣播：已發過就直接結束
if os.path.exists(FLAG_FILE):
    print("✅ 今日廣播已發出，跳過重複發送")
    sys.exit(0)

# 讀取 stories 資料
if not os.path.exists("/tmp/mkt_stories.json"):
    print("❌ /tmp/mkt_stories.json 不存在，廣播取消")
    sys.exit(1)

with open("/tmp/mkt_stories.json", encoding="utf-8") as f:
    data = json.load(f)

stories = data["stories"]
DATE_STR = data["date_str"]
UPDATE_TIME = data["update_time"]

if not stories:
    print("❌ stories 為空，廣播取消")
    sys.exit(1)

print(f"準備廣播 {len(stories)} 則新聞...")

def make_story_box(story, is_last):
    items = [
        {"type": "text", "text": story["title"],
         "weight": "bold", "size": "sm", "color": "#5C4A3D", "wrap": True},
        {"type": "text", "text": story["summary"],
         "size": "xs", "color": "#8B7355", "wrap": True, "margin": "xs"}
    ]
    box = {"type": "box", "layout": "vertical", "spacing": "xs", "contents": items}
    if not is_last:
        return [box, {"type": "separator", "color": "#D4C5B0", "margin": "sm"}]
    return [box]

def section_label(name):
    return {"type": "text", "text": name, "size": "xs",
            "weight": "bold", "color": "#7A8F7A", "margin": "md"}

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
                {"type": "text", "text": "📰 教育 AI 快讀情報",
                 "color": "#FFFFFF", "size": "lg", "weight": "bold"},
                {"type": "text", "text": f"{DATE_STR}　·　共 {len(stories)} 則",
                 "color": "#E0EDD8", "size": "sm", "margin": "xs"},
                {"type": "text", "text": f"🕐 {UPDATE_TIME}",
                 "color": "#C5D9BA", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#F5F0EB", "spacing": "sm",
            "paddingAll": "14px", "contents": body_contents
        },
        "footer": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#F5F0EB", "paddingAll": "12px",
            "contents": [{
                "type": "button",
                "action": {"type": "uri", "label": "開啟快讀版 →", "uri": SITE_URL},
                "style": "primary", "color": "#8BA3B4", "height": "sm"
            }]
        }
    }
}

# ★ broadcast API — 傳給所有好友，絕對不用 push
payload = json.dumps({"messages": [flex_msg]}).encode()
req = urllib.request.Request(
    "https://api.line.me/v2/bot/message/broadcast",
    data=payload,
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {LINE_TOKEN}"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        # ★ 成功後寫 flag，防止後續重複發送
        open(FLAG_FILE, "w").write("ok")
        print(f"✅ LINE 廣播成功！{len(stories)} 則，所有好友都已收到。Status: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"❌ LINE 廣播失敗：HTTP {e.code}")
    print(e.read().decode())
    sys.exit(1)
except Exception as e:
    print(f"❌ LINE 廣播失敗：{e}")
    sys.exit(1)

