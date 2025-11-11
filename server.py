from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os, sys

app = Flask(__name__)

# ✅ เชื่อมต่อ MongoDB
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ ERROR: MONGO_URI not found in environment variables.")
    sys.exit(1)

try:
    client = MongoClient(MONGO_URI)
    db = client["TikTokGiftsDB"]
    gifts_collection = db["gifts"]
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    sys.exit(1)

# 🏠 ตรวจสอบว่าเซิร์ฟเวอร์ทำงานไหม
@app.route("/", methods=["GET"])
def home():
    return "✅ TikTok Gift Multi-User Server is running!"

# 📥 รับของขวัญจาก TikFinity
@app.route("/tiktok-event/<userKey>", methods=["POST"])
def tiktok_event(userKey):
    try:
        # รองรับทั้ง JSON และ Form
        data = request.get_json() if request.is_json else request.form.to_dict()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # เพิ่ม key เพื่อแยกข้อมูลของแต่ละคน
        data["userKey"] = userKey
        gifts_collection.insert_one(data)

        print(f"✅ Gift saved for userKey: {userKey} | {data}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("❌ Error in tiktok_event:", e)
        return jsonify({"error": str(e)}), 500

# 📤 Roblox ดึงของขวัญของตัวเอง
@app.route("/get-latest-gifts/<userKey>", methods=["GET"])
def get_latest_gifts(userKey):
    try:
        gifts = list(gifts_collection.find({"userKey": userKey}).sort("_id", -1).limit(10))
        gifts_to_send = []
        for gift in gifts:
            gift["_id"] = str(gift["_id"])
            gifts_to_send.append(gift)

        # ✅ ลบของขวัญหลังส่ง เพื่อไม่ให้ซ้ำ
        if gifts_to_send:
            ids = [ObjectId(g["_id"]) for g in gifts_to_send]
            gifts_collection.delete_many({"_id": {"$in": ids}})
            print(f"🧹 Cleared {len(ids)} gifts for userKey: {userKey}")

        return jsonify(gifts_to_send), 200
    except Exception as e:
        print("❌ Error in get_latest_gifts:", e)
        return jsonify({"error": str(e)}), 500

# 🧹 เคลียร์ของขวัญทั้งหมด (สำหรับ Dev ใช้เท่านั้น)
@app.route("/clear-gifts/<userKey>", methods=["POST"])
def clear_gifts(userKey):
    try:
        result = gifts_collection.delete_many({"userKey": userKey})
        print(f"🧽 Cleared {result.deleted_count} gifts for {userKey}")
        return jsonify({"status": "cleared", "deleted": result.deleted_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
