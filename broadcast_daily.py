import urllib.request, json, os

LINE_TOKEN = os.environ["LINE_TOKEN_QUICK"]

payload = json.dumps({"messages": [{"type": "text", "text": "測試"}]}).encode()
req = urllib.request.Request(
    "https://api.line.me/v2/bot/message/broadcast",
    data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(f"✅ 成功 Status: {resp.status}")
