from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os
import sys

app = Flask(__name__)

# ==============================================================
# ⚙️ เชื่อมต่อ MongoDB (ใช้ URI จาก Render Environment Variable)
# ==============================================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ ERROR: MONGO_URI not found in environment variables.")
    sys.exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client["TikTokGiftsDB"]
    gifts_collection = db["gifts"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    sys.exit(1)

# ==============================================================
# 📥 Route: รับข้อมูลจาก TikFinity (POST /tiktok-event)
# ==============================================================
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        print("🎁 ได้รับข้อมูลจาก TikFinity:", data)

        # บันทึกลง MongoDB
        gifts_collection.insert_one(data)
        print("✅ บันทึกของขวัญลง MongoDB สำเร็จ!")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("❌ Error saving data to MongoDB:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ==============================================================
# 📤 Route: Roblox ดึงข้อมูลล่าสุด (GET /get-latest-gifts)
# ==============================================================
@app.route("/get-latest-gifts", methods=["GET"])
def get_latest_gifts():
    try:
        # ดึงข้อมูลของขวัญล่าสุดจาก MongoDB (10 รายการล่าสุด)
        gifts = list(gifts_collection.find().sort("_id", -1).limit(10))
        gifts_to_send = []

        for gift in gifts:
            gift["_id"] = str(gift["_id"])
            gifts_to_send.append(gift)

        # 🔥 ลบของขวัญเก่าออกหลังส่งให้ Roblox แล้ว
        if gifts_to_send:
            gift_ids = [g["_id"] for g in gifts_to_send]
            gifts_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in gift_ids]}})
            print(f"🧹 ลบของขวัญเก่าจำนวน {len(gift_ids)} ชิ้นออกจากฐานข้อมูลแล้ว")

        return jsonify(gifts_to_send)

    except Exception as e:
        print("❌ Error fetching gifts:", e)
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 🚀 เริ่มรัน Flask Server
# ==============================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"🌐 Starting Flask server on port {port} ...")
    app.run(host="0.0.0.0", port=port)
