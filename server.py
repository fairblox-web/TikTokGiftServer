from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import os

app = Flask(__name__)

# ===============================================
# 🔐 ตั้งค่า MongoDB และ Password แอดมิน
# ===============================================
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Fairblox123xD")  # ตั้งรหัสผ่านตรงนี้ก็ได้

client = MongoClient(MONGO_URI)
db = client["TikTokGiftsDB"]
keys_col = db["keys"]
gifts_col = db["gifts"]

# ===============================================
# 🧠 Template HTML แผงแอดมิน
# ===============================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>🔧 แผงควบคุมแอดมิน</title>
<style>
    body { background-color: #111; color: white; font-family: Arial; text-align: center; }
    input, select, button { padding: 6px; margin: 4px; border-radius: 4px; border: none; }
    table { width: 90%; margin: auto; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 8px; border-bottom: 1px solid #333; }
    .online { color: #0f0; }
    .offline { color: #888; }
</style>
</head>
<body>
<h2>🔧 แผงควบคุมแอดมิน</h2>

<form method="POST" action="/create-key">
    <input name="key" placeholder="ชื่อคีย์ เช่น FAIRBLOX123" required>
    <select name="days">
        <option value="1">1 วัน</option>
        <option value="7">7 วัน</option>
        <option value="30">30 วัน</option>
        <option value="9999">ถาวร</option>
    </select>
    <button type="submit">สร้างคีย์</button>
</form>

<h3>📜 คีย์ทั้งหมด</h3>
<table>
<tr><th>คีย์</th><th>วันหมดอายุ</th><th>สถานะ</th><th>การใช้งาน</th><th>ออนไลน์</th><th>ลบ</th></tr>
{% for k in keys %}
<tr>
<td>{{ k.key }}</td>
<td>{{ k.expiresAt }}</td>
<td>{{ k.remaining }}</td>
<td>{% if k.used %}🔒 ใช้แล้ว{% else %}🟢 ยังไม่ใช้{% endif %}</td>
<td class="{{ 'online' if k.online else 'offline' }}">{{ 'ออนไลน์' if k.online else 'ออฟไลน์' }}</td>
<td><a href="/delete-key?key={{ k.key }}&password={{ password }}" style="color:red;">ลบ</a></td>
</tr>
{% endfor %}
</table>

</body>
</html>
"""

# ===============================================
# 📦 สร้างคีย์
# ===============================================
@app.route("/create-key", methods=["POST"])
def create_key():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "รหัสผ่านไม่ถูกต้อง ❌", 403

    key_name = request.form["key"]
    days = int(request.form["days"])
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    if days >= 9999:
        expires_at = datetime.max.replace(tzinfo=timezone.utc)

    keys_col.insert_one({
        "key": key_name,
        "createdAt": datetime.now(timezone.utc),
        "expiresAt": expires_at,
        "used": False,
        "boundUserId": None,
        "online": False
    })
    return f"<meta http-equiv='refresh' content='0; url=/admin?password={password}'>"

# ===============================================
# 🧹 ลบคีย์
# ===============================================
@app.route("/delete-key")
def delete_key():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "รหัสผ่านไม่ถูกต้อง ❌", 403
    key = request.args.get("key")
    keys_col.delete_one({"key": key})
    return f"<meta http-equiv='refresh' content='0; url=/admin?password={password}'>"

# ===============================================
# ✅ ตรวจสอบคีย์จาก Roblox
# ===============================================
@app.route("/verify-key", methods=["POST"])
def verify_key():
    data = request.get_json()
    key = data.get("key")
    user_id = data.get("user_id")

    k = keys_col.find_one({"key": key})
    now = datetime.now(timezone.utc)
    if not k:
        return jsonify({"valid": False, "error": "ไม่พบคีย์"})
    if k["expiresAt"] < now:
        keys_col.delete_one({"key": key})
        return jsonify({"valid": False, "error": "คีย์หมดอายุแล้ว"})

    # ผูกคีย์กับ user_id
    if k.get("boundUserId") and k["boundUserId"] != user_id:
        return jsonify({"valid": False, "error": "คีย์นี้ถูกใช้งานโดยผู้อื่นแล้ว"})
    keys_col.update_one({"key": key}, {"$set": {"used": True, "boundUserId": user_id}})
    return jsonify({"valid": True})

# ===============================================
# 🔁 Ping สถานะจาก Roblox
# ===============================================
@app.route("/ping", methods=["POST"])
def ping():
    data = request.get_json()
    key = data.get("key")
    now = datetime.now(timezone.utc)
    keys_col.update_one({"key": key}, {"$set": {"lastPing": now, "online": True}})
    return jsonify({"ok": True})

# ===============================================
# 🌐 API ของขวัญ (ให้ Roblox ดึง)
# ===============================================
@app.route("/get-latest-gifts")
def get_latest_gifts():
    gifts = list(gifts_col.find().sort("_id", -1).limit(10))
    for g in gifts:
        g["_id"] = str(g["_id"])
    return jsonify(gifts)

# ===============================================
# 🧮 แผงควบคุมแอดมิน
# ===============================================
@app.route("/admin")
def admin_panel():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "รหัสผ่านไม่ถูกต้อง ❌", 403

    now = datetime.now(timezone.utc)
    keys = []
    for k in keys_col.find():
        remaining = k["expiresAt"] - now
        remaining_str = f"{remaining.days} วัน" if remaining.days > 0 else "หมดอายุแล้ว"

        # อัปเดตสถานะออนไลน์
        if k.get("lastPing"):
            if (now - k["lastPing"]).total_seconds() > 600:
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
    return render_template_string(ADMIN_HTML, keys=keys, password=password)

# ===============================================
# 🧼 ล้างคีย์หมดอายุ (ทุก 10 นาที)
# ===============================================
@app.before_request
def cleanup_expired_keys():
    now = datetime.now(timezone.utc)
    keys_col.delete_many({"expiresAt": {"$lt": now}})

# ===============================================
# 🚀 เริ่มต้นเซิร์ฟเวอร์
# ===============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
