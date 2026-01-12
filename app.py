from flask import Flask, jsonify, request
import requests
import os
from dotenv import load_dotenv
from sms_alert import send_sms_alert
from routing import get_route
from main import predict   # ML model function import

load_dotenv()

app = Flask(__name__)

# Configuration from .env
FIREBASE_BASE = os.getenv("FIREBASE_URL")
DEVICE_ID = "handbag_001"

@app.route("/")
def home():
    return "SafeBag Backend Running"

# ---------- Health Check ----------
@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "Backend Running"}), 200

# ---------- Get Live Device Location & State ----------
@app.route("/location", methods=["GET"])
def get_location():
    try:
        # Fetching the specific device data from Firebase
        url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        r = requests.get(url, timeout=6)
        data = r.json()
    except Exception as e:
        print(f"Firebase Error: {e}")
        return jsonify({"error": "Firebase unreachable"}), 500

    if not data:
        return jsonify({"error": "No device data found"}), 404

    # Returning all necessary fields including 'acknowledged'
    return jsonify({
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "event_type": data.get("event_type", "NORMAL"),
        "acknowledged": data.get("acknowledged", False),
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

# ---------- Manual SOS (Direct from Button) ----------
@app.route("/sos", methods=["POST"])
def sos_from_app():
    data = request.get_json()
    if not data or "latitude" not in data or "longitude" not in data:
        return jsonify({"error": "Latitude & Longitude required"}), 400

    lat = data["latitude"]
    lon = data["longitude"]

    print(f"📨 Manual SOS Button Pressed → {lat}, {lon}")

    try:
        # For manual SOS, we trigger SMS immediately
        send_sms_alert(lat, lon, event_type="USER_SOS")
        
        # Update Firebase to show this was handled
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True, "event_type": "USER_SOS"})
        
        return jsonify({"message": "SOS Triggered Successfully"}), 200
    except Exception as e:
        print("SOS Error:", e)
        return jsonify({"error": "Failed to trigger SOS"}), 500

# ---------- Police Stations API ----------
@app.route("/police", methods=["GET"])
def get_police():
    police = [
        {"name": "Sitabuldi PS", "lat": 21.1462, "lon": 79.0880},
        {"name": "Sadar PS", "lat": 21.1608, "lon": 79.0781},
        {"name": "Itwari PS", "lat": 21.1485, "lon": 79.1072}
    ]
    return jsonify({"stations": police})

# ---------- Automatic Escalation (Timer expired) ----------
@app.route('/escalate', methods=['POST'])
def escalate():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    event = data.get('event_type')
    
    print(f"🚨 ESCALATING: Emergency {event} at {lat}, {lon}")
    
    # 1. Send the SMS
    try:
        send_sms_alert(lat, lon, event)
    except Exception as e:
        print(f"SMS Function Error: {e}")

    # 2. Update Firebase State
    # This is critical so the Android app stops polling for an active emergency
    try:
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        # We set acknowledged to True so the app clears the popup
        requests.patch(patch_url, json={"acknowledged": True})
    except Exception as e:
        print(f"Firebase State Update Error: {e}")
    
    return jsonify({"status": "success", "message": "Escalation Complete"}), 200

if __name__ == "__main__":
    # Ensure port 8080 is used as per your previous requirement
    app.run(host="0.0.0.0", port=8080)
