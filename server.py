from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "very-secret-key")  # สำหรับ session

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["TikTokGiftsDB"]
gifts_collection = db["gifts"]
keys_collection = db["license_keys"]

# Admin password (ตั้งใน Render Environment)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Fairblox123xD")


# ==========================
# 🧠 หน้า Login Admin
# ==========================
login_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Login | TikTokGiftServer</title>
    <style>
        body { font-family: sans-serif; background-color: #111; color: #fff; text-align: center; margin-top: 100px; }
        input { padding: 10px; border: none; border-radius: 4px; width: 200px; }
        button { padding: 10px 20px; background: #0f0; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body>
    <h2>🔒 เข้าสู่ระบบแอดมิน</h2>
    <form method="POST">
        <input type="password" name="password" placeholder="รหัสผ่านแอดมิน" required><br>
        <button type="submit">เข้าสู่ระบบ</button>
    </form>
    {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
</body>
</html>
"""

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            return render_template_string(login_page, error="รหัสผ่านไม่ถูกต้อง ❌")
    return render_template_string(login_page, error=None)


# ==========================
# 🧩 หน้า Admin หลัก
# ==========================
admin_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    <style>
        body { font-family: sans-serif; background: #0b0b0b; color: white; text-align: center; margin-top: 50px; }
        input, select { padding: 8px; border: none; border-radius: 5px; }
        button { background: #00cc66; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; }
        table { margin: auto; border-collapse: collapse; margin-top: 20px; width: 80%; }
        th, td { border: 1px solid #555; padding: 10px; }
    </style>
</head>
<body>
    <h2>🛠️ แผงควบคุมแอดมิน</h2>
    <form action="/admin/create-key" method="post">
        <input name="key" placeholder="ชื่อคีย์ เช่น FAIRBLOX123" required>
        <select name="duration">
            <option value="1">1 วัน</option>
            <option value="7">7 วัน</option>
            <option value="30">30 วัน</option>
            <option value="9999">ถาวร</option>
        </select>
        <button type="submit">สร้างคีย์</button>
    </form>
    <h3>📜 คีย์ทั้งหมด</h3>
    <table>
        <tr><th>คีย์</th><th>วันหมดอายุ</th><th>สถานะ</th></tr>
        {% for k in keys %}
        <tr>
            <td>{{ k['key'] }}</td>
            <td>{{ k['expires'] }}</td>
            <td>{% if k['active'] %}✅ ใช้งานได้{% else %}❌ หมดอายุ{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/admin")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    keys = list(keys_collection.find({}, {"_id": 0}))
    return render_template_string(admin_page, keys=keys)


@app.route("/admin/create-key", methods=["POST"])
def create_key():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    key_name = request.form["key"]
    duration = int(request.form["duration"])
    expires = datetime.utcnow() + timedelta(days=duration if duration < 9999 else 3650)
    key_data = {"key": key_name, "expires": expires.strftime("%Y-%m-%d %H:%M:%S"), "active": True}
    keys_collection.insert_one(key_data)
    return redirect(url_for("admin_panel"))


# ==========================
# 📦 Webhook จาก Tikfinity
# ==========================
@app.route("/tiktok-event", methods=["POST"])
def tiktok_event():
    data = request.get_json(force=True)
    gifts_collection.insert_one(data)
    return jsonify({"status": "ok"}), 200


# ==========================
# 🎁 ส่งข้อมูลให้ Roblox
# ==========================
@app.route("/get-latest-gifts", methods=["GET"])
def get_latest_gifts():
    gifts = list(gifts_collection.find({}, {"_id": 0}))
    return jsonify(gifts), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
