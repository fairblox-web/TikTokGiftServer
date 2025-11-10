from flask import Flask, request, jsonify

app = Flask(__name__)

latest_gifts = []

@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    # ตรวจสอบว่าข้อมูลที่ส่งมาเป็น JSON หรือไม่
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()  # รองรับกรณี TikFinity ส่งแบบ form data

    print("🎁 ได้รับของขวัญ:", data)
    latest_gifts.append(data)
    return jsonify({"status": "ok"})

@app.route("/get-latest-gifts", methods=["GET"])
def get_latest():
    global latest_gifts
    gifts_to_send = latest_gifts
    latest_gifts = []
    return jsonify(gifts_to_send)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
