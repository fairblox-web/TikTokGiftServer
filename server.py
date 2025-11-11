from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import os

app = Flask(__name__)

# ✅ ดึง URI และ Password จาก Render Environment Variables
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

client = MongoClient(MONGO_URI)
db = client["tiktok_gift_db"]
keys_col = db["license_keys"]

@app.route("/")
def home():
    return "✅ TikTok Gift Server is running!"

# สร้างคีย์ใหม่
@app.route("/create-key", methods=["POST"])
def create_key():
    data = request.json
    key = data.get("key")
    days = int(data.get("days", 7))
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    keys_col.insert_one({
        "key": key,
        "createdAt": datetime.now(timezone.utc),
        "expiresAt": expires_at,
        "used": False,
        "online": False
    })
    return jsonify({"message": f"✅ สร้างคีย์ {key} สำเร็จ!"})

# ตรวจสอบคีย์จาก Roblox
@app.route("/verify-key", methods=["POST"])
def verify_key():
    data = request.json
    key = data.get("key")
    k = keys_col.find_one({"key": key})

    if not k:
        return jsonify({"valid": False, "reason": "ไม่พบคีย์"})

    if datetime.now(timezone.utc) > k["expiresAt"]:
        return jsonify({"valid": False, "reason": "คีย์หมดอายุแล้ว"})

    keys_col.update_one({"key": key}, {"$set": {"used": True}})
    return jsonify({"valid": True})

# Ping สถานะออนไลน์
@app.route("/ping", methods=["POST"])
def ping():
    data = request.json
    key = data.get("key")
    if not key:
        return jsonify({"status": "error", "reason": "ไม่มีคีย์"})
    keys_col.update_one({"key": key}, {"$set": {"online": True, "lastPing": datetime.now(timezone.utc)}})
    return jsonify({"status": "ok"})

# หน้าแอดมิน
@app.route("/admin")
def admin_panel():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "❌ รหัสผ่านไม่ถูกต้อง"

    now = datetime.now(timezone.utc)
    keys = []
    for k in keys_col.find():
        exp = k.get("expiresAt", now)
        remaining_td = exp - now
        remaining = f"{remaining_td.days} วัน" if remaining_td.days > 0 else "หมดอายุแล้ว"

        online = False
        last_ping = k.get("lastPing")
        if last_ping and (now - last_ping).total_seconds() < 300:
            online = True
        else:
            keys_col.update_one({"key": k["key"]}, {"$set": {"online": False}})

        keys.append({
            "key": k["key"],
            "expiresAt": exp.strftime("%Y-%m-%d %H:%M"),
            "remaining": remaining,
            "used": k.get("used", False),
            "online": online
        })

    html = "<h2>🔑 แผงควบคุมแอดมิน</h2><table border=1 cellpadding=4><tr><th>คีย์</th><th>วันหมดอายุ</th><th>เหลือ</th><th>ใช้แล้ว</th><th>สถานะ</th></tr>"
    for k in keys:
        color = "🟢" if k["online"] else "🔴"
        html += f"<tr><td>{k['key']}</td><td>{k['expiresAt']}</td><td>{k['remaining']}</td><td>{k['used']}</td><td>{color}</td></tr>"
    html += "</table>"
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
