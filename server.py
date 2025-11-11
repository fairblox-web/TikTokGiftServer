from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# 🔐 MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["tiktok_gift_db"]
gift_collection = db["gifts"]
key_collection = db["keys"]

# 🌐 หน้าเว็บหลัก
@app.route("/")
def home():
    return "✅ TikTok Gift Server is running with Key System!"

# ✅ สร้างคีย์ใหม่
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        data = request.form
        key_value = data.get("key")
        days = int(data.get("days", 0))
        permanent = data.get("permanent") == "on"
        owner = data.get("owner", "unknown")

        expire_at = None if permanent else datetime.utcnow() + timedelta(days=days)
        key_doc = {
            "key": key_value,
            "is_used": False,
            "expire_at": expire_at,
            "created_at": datetime.utcnow(),
            "owner": owner
        }
        key_collection.insert_one(key_doc)
        return "✅ สร้างคีย์เรียบร้อยแล้ว!"
    
    html = """
    <h2>🔑 สร้างคีย์ใหม่</h2>
    <form method="POST">
        คีย์: <input name="key"><br><br>
        เจ้าของ: <input name="owner"><br><br>
        วันหมดอายุ: <input name="days" type="number" value="7"> วัน<br><br>
        ถาวร: <input type="checkbox" name="permanent"><br><br>
        <button type="submit">สร้างคีย์</button>
    </form>
    """
    return render_template_string(html)

# 🧾 ตรวจสอบคีย์
@app.route("/verify-key", methods=["POST"])
def verify_key():
    data = request.get_json()
    key_value = data.get("key")
    key_data = key_collection.find_one({"key": key_value})

    if not key_data:
        return jsonify({"status": "error", "message": "ไม่พบคีย์นี้"})
    if key_data["is_used"]:
        return jsonify({"status": "error", "message": "คีย์นี้ถูกใช้แล้ว"})
    if key_data["expire_at"] and datetime.utcnow() > key_data["expire_at"]:
        return jsonify({"status": "error", "message": "คีย์นี้หมดอายุแล้ว"})

    key_collection.update_one({"key": key_value}, {"$set": {"is_used": True}})
    return jsonify({"status": "success", "message": "คีย์ถูกต้อง ✅"})

# 🎁 รับของขวัญจาก TikTok (ของเดิม)
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    data = request.get_json() or request.form.to_dict()
    gift_collection.insert_one(data)
    return jsonify({"status": "ok"})

# 📦 ดึงของขวัญล่าสุด (ของเดิม)
@app.route("/get-latest-gifts", methods=["GET"])
def get_latest():
    gifts = list(gift_collection.find())
    gift_collection.delete_many({})
    return jsonify(gifts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
