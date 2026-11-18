from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import random
import time
import requests
import base64

app = Flask(__name__)
load_dotenv()

# ClickSend API credentials
CLICKSEND_USERNAME = os.getenv("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = os.getenv("CLICKSEND_API_KEY")

# OTP store
otp_store = {}
OTP_EXPIRY_SECONDS = 300  # 5 minutes

def generate_otp():
    return str(random.randint(100000, 999999))

def send_sms(to_number, otp):
    message = f"[Rensith Udara] 🔐 Your verification code is: {otp}. It will expire in 5 minutes. Do not share this code with anyone."

    payload = {
        "messages": [
            {
                "source": "python",
                "from": "ClickSend",
                "body": message,
                "to": to_number,
                "schedule": None,
                "custom_string": "otp-verification"
            }
        ]
    }

    auth_string = f"{CLICKSEND_USERNAME}:{CLICKSEND_API_KEY}"
    auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    headers = {
        "Authorization": f"Basic {auth_bytes}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://rest.clicksend.com/v3/sms/send",
        headers=headers,
        json=payload
    )

    return response

@app.route("/send-phone-otp", methods=["POST"])
def send_phone_otp():
    data = request.json
    phone = data.get("phone")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    otp = generate_otp()
    timestamp = int(time.time())

    response = send_sms(phone, otp)

    if response.status_code == 200:
        otp_store[phone] = (otp, timestamp)
        return jsonify({"message": "OTP sent via ClickSend SMS"}), 200
    else:
        return jsonify({"error": response.json()}), response.status_code

@app.route("/verify-phone-otp", methods=["POST"])
def verify_phone_otp():
    data = request.json
    phone = data.get("phone")
    user_otp = data.get("otp")

    if not phone or not user_otp:
        return jsonify({"error": "Phone and OTP are required"}), 400

    record = otp_store.get(phone)

    if not record:
        return jsonify({"error": "No OTP found for this phone"}), 404

    stored_otp, timestamp = record
    if int(time.time()) - timestamp > OTP_EXPIRY_SECONDS:
        del otp_store[phone]
        return jsonify({"error": "OTP expired"}), 400

    if user_otp != stored_otp:
        return jsonify({"error": "Invalid OTP"}), 401

    del otp_store[phone]
    return jsonify({"message": "OTP verified successfully!"}), 200

if __name__ == "__main__":
    app.run(debug=True)
