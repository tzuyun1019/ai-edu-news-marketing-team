import json, re, os, urllib.request
from datetime import datetime

LINE_TOKEN_DEEP = os.environ.get("LINE_TOKEN_DEEP", "")
LINE_USER_DEEP  = os.environ.get("LINE_USER_DEEP", "")
SITE_URL        = os.environ.get("SITE_URL", "https://tzuyun1019.github.io/ai-edu-news-marketing-team/")

# ── 讀取 index.html，找到未加 hidden 的 day-pane ──
with open("index.html", encoding="utf-8") as f:
    html = f.read()

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

stories = []
for raw in re.findall(r"data-story='(\{[^']+\})'", active_html):
    try:
        stories.append(json.loads(raw))
    except Exception as e:
        print(f"JSON parse error: {e}")

if not stories:
    print("沒有找到 stories，跳過推播")
    exit(0)

dt = datetime.strptime(active_date, "%Y-%m-%d")
dow_map = {0:"週一",1:"週二",2:"週三",3:"週四",4:"週五",5:"週六",6:"週日"}
DATE_STR = f"{dt.year}年{dt.month}月{dt.day}日（{dow_map[dt.weekday()]}）"

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

# ── 深度版草稿純文字（給 Michelle 參考，用於 LINE OA 發文） ──
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

# 快讀版 Flex 由 daily_broadcast.yml broadcast 負責，這裡不重複推播
if LINE_TOKEN_DEEP and LINE_USER_DEEP:
    line_push(LINE_TOKEN_DEEP, LINE_USER_DEEP,
              [{"type": "text", "text": build_draft_text()}])
else:
    print("LINE_TOKEN_DEEP 未設定，跳過深度版草稿推播")
