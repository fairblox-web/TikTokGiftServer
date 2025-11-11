from flask import Flask, request, jsonify

app = Flask(__name__)

# ตัวแปรเก็บของขวัญล่าสุด
latest_gifts = []


# 🟣 Route สำหรับรับของขวัญจาก TikFinity
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()  # เผื่อกรณีส่งแบบ form data

    print("🎁 ได้รับของขวัญ:", data)
    latest_gifts.append(data)
    return jsonify({"status": "ok"})


# 🟢 Route สำหรับ Roblox ดึงข้อมูลของขวัญล่าสุด
@app.route("/get-latest-gifts", methods=["GET"])
def get_latest():
    global latest_gifts
    gifts_to_send = latest_gifts
    latest_gifts = []  # เคลียร์หลังส่ง
    return jsonify(gifts_to_send)


# 🔵 Route สำหรับเคลียร์ของขวัญทั้งหมด (ใช้ตอน debug หรือ reset)
@app.route("/clear-gifts", methods=["POST"])
def clear_gifts():
    global latest_gifts
    latest_gifts = []
    print("🧹 Cleared all stored gifts.")
    return jsonify({"status": "cleared"})


# 🚀 รัน Flask เซิร์ฟเวอร์
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
