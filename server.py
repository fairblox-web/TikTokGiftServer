from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import threading
import time
import os

app = Flask(__name__)

# ✅ MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["TikTokGiftsDB"]
gifts_col = db["gifts"]
keys_col = db["keys"]

# ✅ Admin password (ตั้งใน Render Environment Variable)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Fairblox123xD")


# ==========================================================
# 🎁 ระบบของขวัญเดิม
# ==========================================================
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    data = request.get_json(force=True)
    gifts_col.insert_one({
        "username": data.get("username", "Unknown"),
        "giftName": data.get("giftName", "Unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    print(f"🎁 ได้รับของขวัญจาก {data.get('username')} : {data.get('giftName')}")
    return jsonify({"status": "ok"})


@app.route("/get-latest-gifts", methods=["GET"])
def get_latest():
    docs = list(gifts_col.find({}, {"_id": 0}))
    gifts_col.delete_many({})
    return jsonify(docs)


# ==========================================================
# 🔐 ระบบ Key Manager
# ==========================================================
@app.route("/verify-key", methods=["POST"])
def verify_key():
    data = request.get_json(force=True)
    key = data.get("key")
    user_id = data.get("user_id")

    record = keys_col.find_one({"key": key})
    if not record:
        return jsonify({"success": False, "message": "❌ ไม่พบคีย์นี้ในระบบ"})

    # ตรวจหมดอายุ
    if datetime.now(timezone.utc) > record["expiresAt"]:
        keys_col.delete_one({"key": key})
        return jsonify({"success": False, "message": "⏰ คีย์หมดอายุแล้ว"})

    # ยังไม่เคยใช้
    if not record.get("used"):
        keys_col.update_one(
            {"key": key},
            {"$set": {
                "used": True,
                "usedAt": datetime.now(timezone.utc),
                "boundUserId": user_id,
                "online": True,
                "lastPing": datetime.now(timezone.utc)
            }}
        )
        return jsonify({"success": True, "message": "✅ ยืนยันคีย์สำเร็จ (ผูกกับบัญชีนี้แล้ว)"})

    # ใช้แล้วแต่คนเดิม
    if record.get("boundUserId") == user_id:
        keys_col.update_one({"key": key}, {"$set": {"online": True, "lastPing": datetime.now(timezone.utc)}})
        return jsonify({"success": True, "message": "✅ ยืนยันคีย์สำเร็จ (บัญชีเดิม)"})

    # ใช้แล้วแต่คนอื่น
    return jsonify({"success": False, "message": "🚫 คีย์นี้ถูกใช้ไปแล้ว"})


@app.route("/update-online", methods=["POST"])
def update_online():
    data = request.get_json(force=True)
    key = data.get("key")
    user_id = data.get("user_id")

    record = keys_col.find_one({"key": key})
    if record and record.get("boundUserId") == user_id:
        keys_col.update_one({"key": key}, {"$set": {"lastPing": datetime.now(timezone.utc), "online": True}})
        return jsonify({"status": "pong"})
    return jsonify({"status": "fail"})


# ==========================================================
# 🧹 ลบคีย์หมดอายุอัตโนมัติ
# ==========================================================
def cleanup_expired_keys():
    while True:
        now = datetime.now(timezone.utc)
        expired = list(keys_col.find({"expiresAt": {"$lt": now}}))
        for key in expired:
            keys_col.delete_one({"_id": key["_id"]})
            print(f"🗑️ ลบคีย์หมดอายุ: {key['key']}")
        time.sleep(600)  # ทุก 10 นาที


cleanup_thread = threading.Thread(target=cleanup_expired_keys, daemon=True)
cleanup_thread.start()


# ==========================================================
# 🧭 หน้า Admin Panel
# ==========================================================
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Admin Panel</title>
  <style>
    body { background:#111; color:#eee; font-family:sans-serif; }
    h1 { color:#4CAF50; }
    table { border-collapse:collapse; width:100%; margin-top:20px; }
    th,td { border:1px solid #333; padding:8px; text-align:center; }
    tr:nth-child(even){background-color:#1e1e1e;}
    .ok { color:#4CAF50; }
    .bad { color:#f44336; }
    button { background:#333; color:#fff; border:none; padding:6px 10px; cursor:pointer; }
    button:hover { background:#4CAF50; }
  </style>
</head>
<body>
<h1>🔐 Fairblox Admin Panel</h1>
<form method="get">
  <input type="password" name="password" placeholder="Admin Password" required>
  <button type="submit">เข้าสู่ระบบ</button>
</form>

{% if valid %}
  <form method="post" action="/create-key">
    <input type="hidden" name="password" value="{{ password }}">
    <input type="text" name="key" placeholder="ชื่อคีย์" required>
    <input type="number" name="days" placeholder="จำนวนวัน" required>
    <button type="submit">➕ สร้างคีย์ใหม่</button>
  </form>

  <table>
    <tr><th>คีย์</th><th>วันหมดอายุ</th><th>เหลือเวลา</th><th>สถานะ</th><th>ผู้ใช้</th><th>ออนไลน์</th><th>ลบ</th></tr>
    {% for k in keys %}
      <tr>
        <td>{{k.key}}</td>
        <td>{{k.expiresAt}}</td>
        <td>{{k.remaining}}</td>
        <td>{{"🟢 ใช้งานแล้ว" if k.used else "⚪ ยังไม่ใช้"}}</td>
        <td>{{k.boundUserId or "-"}}</td>
        <td>{{"🟢" if k.online else "🔴"}}</td>
        <td>
          <form method="post" action="/delete-key" style="margin:0">
            <input type="hidden" name="password" value="{{ password }}">
            <input type="hidden" name="key" value="{{k.key}}">
            <button>ลบ</button>
          </form>
        </td>
      </tr>
    {% endfor %}
  </table>
{% endif %}
</body>
</html>
"""


@app.route("/admin", methods=["GET"])
def admin_panel():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return render_template_string(HTML_ADMIN, valid=False)

    now = datetime.now(timezone.utc)
    keys = []
    for k in keys_col.find():
        remaining = k["expiresAt"] - now
        remaining_str = f"{remaining.days} วัน" if remaining.days > 0 else "หมดอายุแล้ว"
        # อัปเดตสถานะออนไลน์ (ถ้าเกิน 5 นาทีถือว่าออฟไลน์)
        if k.get("lastPing"):
            if (now - k["lastPing"]).total_seconds() > 300:
                k["online"] = False
                keys_col.update_one({"key": k["key"]}, {"$set": {"online": False}})
        keys.append({
            "key": k["key"],
            "expiresAt": k["expiresAt"].strftime("%Y-%m-%d %H:%M"),
            "remaining": remaining_str,
            "used": k.get("used", False),
            "boundUserId": k.get("boundUserId"),
            "online": k.get("online", False)
        })

    return render_template_string(HTML_ADMIN, valid=True, keys=keys, password=password)


@app.route("/create-key", methods=["POST"])
def create_key():
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "❌ รหัสไม่ถูกต้อง"

    key = request.form.get("key")
    days = int(request.form.get("days", 7))
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=days)
    keys_col.insert_one({
        "key": key,
        "durationDays": days,
        "createdAt": now,
        "expiresAt": expires,
        "used": False,
        "online": False
    })
    return "<script>location.href=document.referrer;</script>"


@app.route("/delete-key", methods=["POST"])
def delete_key():
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "❌ รหัสไม่ถูกต้อง"
    key = request.form.get("key")
    keys_col.delete_one({"key": key})
    return "<script>location.href=document.referrer;</script>"


# ==========================================================
# ✅ Run Server
# ==========================================================
@app.route("/")
def home():
    return "✅ TikTok Gift + Key Server is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
