from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId  # ✅ ใช้แปลง _id จาก MongoDB
import os
import sys

app = Flask(__name__)

# ------------------------------------------------------
# ✅ โหลด URI ของ MongoDB จาก Environment บน Render
# ------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ ไม่พบตัวแปร MONGO_URI ใน Environment")
    sys.exit(1)

# ------------------------------------------------------
# ✅ เชื่อมต่อกับ MongoDB
# ------------------------------------------------------
try:
    client = MongoClient(MONGO_URI)
    db = client["TikTokGiftsDB"]          # ชื่อฐานข้อมูล
    gifts_collection = db["gifts"]        # ชื่อคอลเล็กชัน
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    sys.exit(1)

# ------------------------------------------------------
# ✅ ตัวแปรเก็บของขวัญล่าสุด (ใช้สำหรับ Roblox)
# ------------------------------------------------------
latest_gifts = []

# ------------------------------------------------------
# ✅ Route: รับ webhook จาก TikFinity
# ------------------------------------------------------
@app.route('/tiktok-event', methods=['POST'])
def tiktok_event():
    global latest_gifts
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        print("🎁 ได้รับข้อมูลจาก TikFinity:", data, flush=True)

        # บันทึกลง MongoDB
        gifts_collection.insert_one(data)
        latest_gifts.append(data)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("❌ เกิดข้อผิดพลาดตอนบันทึก MongoDB:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------
# ✅ Route: สำหรับ Roblox เรียกดูของขวัญล่าสุด
# ------------------------------------------------------
@app.route('/get-latest-gifts', methods=['GET'])
def get_latest_gifts():
    try:
        gifts_to_send = []
        for gift in gifts_collection.find().sort("_id", -1).limit(20):  # ส่ง 20 ชิ้นล่าสุด
            gift['_id'] = str(gift['_id'])  # ✅ แปลง ObjectId เป็น string
            gifts_to_send.append(gift)
        return jsonify(gifts_to_send), 200
    except Exception as e:
        print("❌ เกิดข้อผิดพลาดตอนดึงข้อมูล:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------
# ✅ Route พื้นฐานตรวจว่าเซิร์ฟเวอร์ออนไลน์ไหม
# ------------------------------------------------------
@app.route('/')
def index():
    return jsonify({"status": "server is live"}), 200

# ------------------------------------------------------
# ✅ เริ่มรัน Flask
# ------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
