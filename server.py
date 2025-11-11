from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import time
import os

app = Flask(__name__)

# ==========================
# ⚙️ การเชื่อมต่อฐานข้อมูล MongoDB
# ==========================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["TikTokGiftsDB"]
gifts_col = db["gifts"]
keys_col = db["keys"]

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Fairblox123xD")

# ==========================
# 🎁 ระบบของขวัญ (ของเดิม)
# ==========================
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    data = request.get_json(force=True)
    print("🎁 ได้รับของขวัญ:", data)
    gifts_col.insert_one({
        "username": data.get("username"),
        "giftName": data.get("giftName"),
        "timestamp": datetime.utcnow()
    })
    return jsonify({"status": "ok"})

@app.route("/get-latest-gifts", methods=["GET"])
def get_latest_gifts():
    gifts = list(gifts_col.find())
    gifts_col.delete_many({})
    return jsonify(gifts)

# ==========================
# 🔐 ระบบ Key Verification
# ==========================
@app.route("/create-key", methods=["POST"])
def create_key():
    data = request.get_json(force=True)
    key = data.get("key")
    duration = int(data.get("durationDays", 7))

    if keys_col.find_one({"key": key}):
        return jsonify({"error": "Key already exists"}), 400

    now = datetime.utcnow()
    expires_at = now + timedelta(days=duration)
    keys_col.insert_one({
        "key": key,
        "durationDays": duration,
        "createdAt": now,
        "expiresAt": expires_at,
        "used": False,
        "boundUserId": None,
        "online": False
    })
    return jsonify({"status": "Key created", "key": key})

@app.route("/verify-key", methods=["POST"])
def verify_key():
    data = request.get_json(force=True)
    key = data.get("key")
    user_id = data.get("userId")

    key_data = keys_col.find_one({"key": key})
    if not key_data:
        return jsonify({"valid": False, "reason": "Key not found"})

    if datetime.utcnow() > key_data["expiresAt"]:
        keys_col.delete_one({"key": key})
        return jsonify({"valid": False, "reason": "Key expired and deleted"})

    if key_data["used"] and key_data["boundUserId"] != user_id:
        return jsonify({"valid": False, "reason": "Key already used by another user"})

    keys_col.update_one(
        {"key": key},
        {"$set": {"used": True, "boundUserId": user_id, "online": True, "usedAt": datetime.utcnow()}}
    )
    return jsonify({"valid": True, "expiresAt": key_data["expiresAt"].isoformat()})

@app.route("/update-online", methods=["POST"])
def update_online():
    data = request.get_json(force=True)
    key = data.get("key")
    key_data = keys_col.find_one({"key": key})
    if not key_data:
        return jsonify({"status": "error", "reason": "key not found"}), 404
    keys_col.update_one({"key": key}, {"$set": {"online": True, "lastPing": datetime.utcnow()}})
    return jsonify({"status": "ok"})

# ==========================
# 🧹 ระบบลบคีย์อัตโนมัติ
# ==========================
def auto_cleanup():
    while True:
        now = datetime.utcnow()
        expired = keys_col.find({"expiresAt": {"$lt": now}})
        count = 0
        for key in expired:
            keys_col.delete_one({"_id": key["_id"]})
            count += 1
        if count > 0:
            print(f"🧹 ลบคีย์หมดอายุไปแล้ว {count} รายการ")
        time.sleep(600)  # ทุก 10 นาที

threading.Thread(target=auto_cleanup, daemon=True).start()

# ==========================
# 🧑‍💼 หน้าแอดมิน
# ==========================
@app.route("/admin", methods=["GET"])
def admin_page():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "<h3 style='color:red;'>รหัสผ่านไม่ถูกต้อง ❌</h3>"

    keys = list(keys_col.find())
    html = """
    <h2>🛠️ แผงควบคุมระบบ Key (Fairblox)</h2>
    <table border="1" cellpadding="5">
      <tr><th>Key</th><th>วันหมดอายุ</th><th>เหลือเวลา</th><th>ผู้ใช้</th><th>สถานะ</th><th>การจัดการ</th></tr>
      {% for k in keys %}
      <tr>
        <td>{{k['key']}}</td>
        <td>{{k['expiresAt']}}</td>
        <td>
            {% if k['expiresAt'] %}
                {{ ((k['expiresAt'] - now).days) }} วัน
            {% else %}
                -
            {% endif %}
        </td>
        <td>{{k.get('boundUserId', '-') }}</td>
        <td>{% if k.get('online') %}🟢 ออนไลน์{% else %}🔴 ออฟไลน์{% endif %}</td>
        <td><form method="POST" action="/delete-key"><input type="hidden" name="key" value="{{k['key']}}"><input type="submit" value="ลบคีย์"></form></td>
      </tr>
      {% endfor %}
    </table>
    <br><h3>➕ สร้างคีย์ใหม่</h3>
    <form method="POST" action="/create-key-form">
        <input name="key" placeholder="ชื่อคีย์">
        <input name="days" placeholder="จำนวนวัน" type="number" min="1">
        <input type="submit" value="สร้างคีย์">
    </form>
    """
    return render_template_string(html, keys=keys, now=datetime.utcnow())

@app.route("/create-key-form", methods=["POST"])
def create_key_form():
    key = request.form.get("key")
    days = int(request.form.get("days", 7))
    now = datetime.utcnow()
    expires_at = now + timedelta(days=days)
    keys_col.insert_one({
        "key": key,
        "durationDays": days,
        "createdAt": now,
        "expiresAt": expires_at,
        "used": False,
        "boundUserId": None,
        "online": False
    })
    return "<script>alert('✅ สร้างคีย์สำเร็จ!');location.href='/admin?password="+ADMIN_PASSWORD+"';</script>"

@app.route("/delete-key", methods=["POST"])
def delete_key():
    key = request.form.get("key")
    keys_col.delete_one({"key": key})
    return "<script>alert('🗑️ ลบคีย์สำเร็จ!');location.href='/admin?password="+ADMIN_PASSWORD+"';</script>"

# ==========================
# 🏠 หน้าแรก
# ==========================
@app.route("/")
def home():
    return "✅ TikTok Gift & Key Server is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
