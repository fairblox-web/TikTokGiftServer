from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from datetime import datetime

app = Flask(__name__)

# ✅ เชื่อมต่อ MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["TikTokGiftsDB"]
collection = db["gifts"]

# 🧾 รายชื่อ key ที่อนุญาต (เพิ่มได้เรื่อย ๆ)
AUTHORIZED_KEYS = {
    "fairblox": "ABC123",
    "mint": "XYZ999",
    "don": "777TTT"
}

# 📦 รับของขวัญจาก TikFinity
@app.route("/tiktok-event/<userKey>", methods=["POST"])
def tiktok_event(userKey):
    try:
        # ✅ ตรวจสอบ key จาก query string
        provided_key = request.args.get("key")
        if not provided_key or AUTHORIZED_KEYS.get(userKey) != provided_key:
            print(f"🚫 Unauthorized access attempt for {userKey} with key={provided_key}")
            return jsonify({"error": "Invalid or missing key"}), 403

        # ✅ รองรับข้อมูลทั้ง JSON และ form
        data = request.get_json(silent=True) or request.form.to_dict()
        if not data:
            return jsonify({"error": "Invalid data"}), 400

        data["userKey"] = userKey
        data["timestamp"] = datetime.utcnow()
        collection.insert_one(data)

        print(f"✅ Gift saved for {userKey}: {data}")
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Error saving gift:", e)
        return jsonify({"error": str(e)}), 500


# 📤 Roblox จะดึงข้อมูลของขวัญจากตรงนี้
@app.route("/get-latest-gifts/<userKey>", methods=["GET"])
def get_latest(userKey):
    try:
        gifts = list(collection.find({"userKey": userKey}, {"_id": 0}))
        collection.delete_many({"userKey": userKey})
        print(f"🧹 Cleared {len(gifts)} gifts for userKey: {userKey}")
        return jsonify(gifts)
    except Exception as e:
        print("❌ Error fetching gifts:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return jsonify({"status": "✅ TikTok Gift Server with AuthKey is running!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
