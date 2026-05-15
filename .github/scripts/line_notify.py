import json, re, os, urllib.request
from datetime import datetime

LINE_TOKEN_MKT  = os.environ.get("LINE_TOKEN_MKT", "")
LINE_USER_MKT   = os.environ.get("LINE_USER_MKT", "")
LINE_TOKEN_DEEP = os.environ.get("LINE_TOKEN_DEEP", "")
LINE_USER_DEEP  = os.environ.get("LINE_USER_DEEP", "")
SITE_URL        = os.environ.get("SITE_URL", "https://tzuyun1019.github.io/ai-edu-news-marketing-team/")

# ── 讀取 index.html，找到未加 hidden 的 day-pane ──
with open("index.html", encoding="utf-8") as f:
    html = f.read()

# 找出所有 day-pane section tags（含屬性），保留無 hidden 的那一個
section_re = re.compile(
    r'(<section\s[^>]*class="day-pane"[^>]*>)(.*?)</section>',
    re.DOTALL
)

active_date = None
active_html = None

for m in section_re.finditer(html):
    tag, body = m.group(1), m.group(2)
    date_m = re.search(r'data-day="(\d{4}-\d{2}-\d{2})"', tag)
    if date_m and "hidden" not in tag and "emptyPane" not in tag:
        active_date = date_m.group(1)
        active_html = body
        break

if not active_html:
    print("找不到 active day-pane，跳過推播")
    exit(0)

# ── 擷取 data-story JSON ──
stories = []
for raw in re.findall(r"data-story='(\{[^']+\})'", active_html):
    try:
        stories.append(json.loads(raw))
    except Exception as e:
        print(f"JSON parse error: {e}")

if not stories:
    print("沒有找到 stories，跳過推播")
    exit(0)

# ── 日期字串 ──
dt = datetime.strptime(active_date, "%Y-%m-%d")
dow_map = {0:"週一",1:"週二",2:"週三",3:"週四",4:"週五",5:"週六",6:"週日"}
DATE_STR = f"{dt.year}年{dt.month}月{dt.day}日（{dow_map[dt.weekday()]}）"


# ── LINE API 推送 helper ──
def line_push(token, user_id, messages):
    payload = json.dumps({"to": user_id, "messages": messages}).encode()
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"推播成功 → {user_id[:8]}... status={resp.status}")
    except Exception as e:
        print(f"推播失敗 → {user_id[:8]}...: {e}")


# ── 快讀版 Flex Message（同事） ──
def build_flex():
    def section_label(name):
        return {"type": "text", "text": name, "size": "xs",
                "weight": "bold", "color": "#7A8F7A", "margin": "md"}

    def story_box(s, is_last):
        box = {"type": "box", "layout": "vertical", "spacing": "xs", "contents": [
            {"type": "text", "text": s["title"],
             "weight": "bold", "size": "sm", "color": "#5C4A3D", "wrap": True},
        ]}
        if not is_last:
            return [box, {"type": "separator", "color": "#D4C5B0", "margin": "sm"}]
        return [box]

    body = []
    cur_sec = None
    for i, s in enumerate(stories):
        if s.get("section") != cur_sec:
            cur_sec = s.get("section")
            body.append(section_label(cur_sec))
        body.extend(story_box(s, i == len(stories) - 1))

    return {
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
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#F5F0EB", "spacing": "sm",
                "paddingAll": "14px", "contents": body
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


# ── 深度版草稿純文字（Michelle） ──
def build_draft_text():
    lines = [f"📰 教育 AI 快讀情報｜{DATE_STR}", ""]
    cur_sec = None
    for s in stories:
        sec = s.get("section", "")
        if sec != cur_sec:
            cur_sec = sec
            lines.append(f"【{sec}】")
        lines.append(f"▸ {s['title']}")
        takeaway = s.get("takeaway", "")
        if takeaway:
            lines.append(takeaway)
        lines.append("")
    lines.append(f"🔗 查看完整快讀版：{SITE_URL}")
    lines.append("")
    lines.append("――――――――――")
    lines.append("⬆️ 以上為 LINE 官方帳號貼文串草稿，請自行複製至 LINE OA Manager 發布。")
    return "\n".join(lines)


# ── 執行推播 ──
if LINE_TOKEN_MKT and LINE_USER_MKT:
    line_push(LINE_TOKEN_MKT, LINE_USER_MKT, [build_flex()])
else:
    print("LINE_TOKEN_MKT 未設定，跳過快讀版推播")

if LINE_TOKEN_DEEP and LINE_USER_DEEP:
    line_push(LINE_TOKEN_DEEP, LINE_USER_DEEP,
              [{"type": "text", "text": build_draft_text()}])
else:
    print("LINE_TOKEN_DEEP 未設定，跳過深度版草稿推播")
