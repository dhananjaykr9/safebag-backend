from flask import Flask, jsonify, request
import requests
import os
from dotenv import load_dotenv
from sms_alert import send_sms_alert
# Ensure these files exist in your project folder
from routing import get_fast_route, get_safe_route
from ml_engine import predict    

load_dotenv()

app = Flask(__name__)

# Configuration
FIREBASE_BASE = os.getenv("FIREBASE_URL")
DEVICE_ID = "handbag_001"

@app.route("/")
def home():
    return "SafeBag Backend Running (Fixed Version)"

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
    except Exception as e:
        # Return 200 with error status so App displays it, rather than failing silently
        return jsonify({
            "event_type": "SERVER_ERROR", 
            "latitude": 0.0, 
            "longitude": 0.0
        }), 200

    # FIX: Don't return 404. Return 200 with defaults so the App UI updates.
    if not data:
        return jsonify({
            "latitude": 0.0,
            "longitude": 0.0,
            "event_type": "WAITING_FOR_DATA",
            "acknowledged": True,
            "timestamp": 0
        }), 200

    return jsonify({
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "event_type": data.get("event_type", "NORMAL"),
        "acknowledged": data.get("acknowledged", False),
        "timestamp": data.get("timestamp_ms")
    }), 200

# ---------- DUAL ROUTE API ----------
@app.route("/route", methods=["GET"])
def route_api():
    try:
        start_lat = float(request.args.get("start_lat"))
        start_lon = float(request.args.get("start_lon"))
        end_lat   = float(request.args.get("end_lat"))
        end_lon   = float(request.args.get("end_lon"))

        fast = get_fast_route(start_lat, start_lon, end_lat, end_lon)
        safe = get_safe_route(start_lat, start_lon, end_lat, end_lon)

        return jsonify({
            "fast_route": fast,
            "safe_route": safe
        }), 200
    except Exception as e:
        print(f"Routing Error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------- ML PREDICTION API ----------
@app.route("/predict", methods=["GET"])
def predict_api():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))

        risk, crime, probability = predict(lat, lon)
        
        return jsonify({
            "risk": risk, 
            "crime": crime,
            "safety_probability": probability
        }), 200
    except Exception as e:
        print(f"ML Error: {e}")
        # Return defaults on error to prevent app crash
        return jsonify({"risk": "Unknown", "crime": "Unknown", "safety_probability": 0.5}), 200

# ---------- MISSING ROUTE 1: Police Stations ----------
@app.route("/police", methods=["GET"])
def get_police():
    # Placeholder: Return empty list or nearby stations logic
    return jsonify({
        "stations": [] 
    }), 200

# ---------- MISSING ROUTE 2: Send Acknowledge ----------
@app.route("/send_ack", methods=["POST"])
def send_ack():
    try:
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        # Update Firebase so the bag stops beeping (if hardware connected)
        requests.patch(patch_url, json={"acknowledged": True, "event_type": "SAFE"})
        return jsonify({"status": "acknowledged"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Manual SOS ----------
@app.route("/sos", methods=["POST"])
def sos_from_app():
    data = request.get_json()
    if not data or "latitude" not in data:
        return jsonify({"error": "Location required"}), 400

    lat = data["latitude"]
    lon = data["longitude"]
    
    print(f"📨 Manual SOS → {lat}, {lon}")

    try:
        send_sms_alert(lat, lon, event_type="USER_SOS")
        
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True, "event_type": "USER_SOS"})
        
        return jsonify({"message": "SOS Sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Auto Escalation ----------
@app.route('/escalate', methods=['POST'])
def escalate():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    event = data.get('event_type')
    
    print(f"🚨 ESCALATING: {event}")
    
    try:
        send_sms_alert(lat, lon, event)
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True})
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
