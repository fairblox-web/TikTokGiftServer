from flask import Flask, request, jsonify
from pymongo import MongoClient
import sys

app = Flask(__name__)

# --------------------------------------------------------
# 🧠 เชื่อมต่อ MongoDB (ใช้ข้อมูลของคุณ)
# --------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
try:
    client = MongoClient(MONGO_URI)
    db = client["TikTokGiftsDB"]          # ชื่อ Database
    gifts_collection = db["gifts"]        # ชื่อ Collection
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    sys.exit(1)

# --------------------------------------------------------
# 🕹️ ตัวแปรเก็บของขวัญล่าสุด (สำหรับ Roblox ดึง)
# --------------------------------------------------------
latest_gifts = []

# --------------------------------------------------------
# 📦 Route: รับ Webhook จาก TikFinity
# --------------------------------------------------------
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    global latest_gifts

    # รับข้อมูลจาก TikFinity
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    print("🎁 ได้รับของขวัญจาก TikTok:", data)
    sys.stdout.flush()

    # บันทึกลง MongoDB
    try:
        gifts_collection.insert_one(data)
        print("✅ บันทึกข้อมูลของขวัญลง MongoDB สำเร็จ")
    except Exception as e:
        print("❌ เกิดข้อผิดพลาดในการบันทึก:", e)

    # เก็บไว้ให้ Roblox ดึงด้วย
    latest_gifts.append(data)

    return jsonify({"status": "ok"})

# --------------------------------------------------------
# 🧩 Route: ให้ Roblox ดึงข้อมูลของขวัญล่าสุด
# --------------------------------------------------------
@app.route("/get-latest-gifts", methods=["GET"])
def get_latest_gifts():
    global latest_gifts
    gifts_to_send = latest_gifts
    latest_gifts = []
    return jsonify(gifts_to_send)

# --------------------------------------------------------
# 🧹 Route: ล้างข้อมูลของขวัญทั้งหมด (ใช้ตอนดีบั๊ก)
# --------------------------------------------------------
@app.route("/clear-gifts", methods=["POST"])
def clear_gifts():
    global latest_gifts
    latest_gifts = []
    gifts_collection.delete_many({})
    print("🧹 ล้างข้อมูลทั้งหมดเรียบร้อยแล้ว")
    sys.stdout.flush()
    return jsonify({"status": "cleared"})

# --------------------------------------------------------
# 🚀 เริ่มรัน Flask บน Render
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
