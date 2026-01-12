from flask import Flask, jsonify, request
import requests, os
from dotenv import load_dotenv
from sms_alert import send_sms_alert
from routing import get_route
from main import predict   # 🔹 ML model function import

load_dotenv()

app = Flask(__name__)

FIREBASE_BASE = os.getenv("FIREBASE_URL")
DEVICE_ID = "handbag_001"

# ---------- Health Check ----------
@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "Backend Running"}), 200


# ---------- Get Live Device Location ----------
@app.route("/location", methods=["GET"])
def get_location():
    try:
        url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        r = requests.get(url, timeout=6)
        data = r.json()
    except Exception:
        return jsonify({"error": "Firebase unreachable"}), 500

    if not data:
        return jsonify({"error": "No device data"}), 404

    return jsonify({
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "event_type": data.get("event_type", "NORMAL"),
        "timestamp": data.get("timestamp_ms")
    }), 200


# ---------- SAFE ROUTE API ----------
@app.route("/route", methods=["GET"])
def route_api():
    try:
        start_lat = float(request.args.get("start_lat"))
        start_lon = float(request.args.get("start_lon"))
        end_lat   = float(request.args.get("end_lat"))
        end_lon   = float(request.args.get("end_lon"))

        route = get_route(start_lat, start_lon, end_lat, end_lon)
        return jsonify({"route": route}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- ML RISK PREDICTION API ----------
@app.route("/predict", methods=["GET"])
def predict_api():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))

        risk, crime = predict(lat, lon)
        return jsonify({"risk": risk, "crime": crime}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- SOS Trigger from Android App ----------
@app.route("/sos", methods=["POST"])
def sos_from_app():
    data = request.get_json()

    if not data or "latitude" not in data or "longitude" not in data:
        return jsonify({"error": "Latitude & Longitude required"}), 400

    lat = data["latitude"]
    lon = data["longitude"]

    print(f"📨 SOS from Android App → {lat}, {lon}")

    try:
        send_sms_alert(lat, lon, event_type="MOBILE_APP")
    except Exception as e:
        print("SMS Error:", e)

    return jsonify({"message": "SOS Triggered Successfully"}), 200


@app.route("/police", methods=["GET"])
def get_police():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    police = [
        {"name":"Sitabuldi PS","lat":21.1462,"lon":79.0880},
        {"name":"Sadar PS","lat":21.1608,"lon":79.0781},
        {"name":"Itwari PS","lat":21.1485,"lon":79.1072}
    ]
    return jsonify({"stations": police})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
