from flask import Flask, jsonify, request
import requests
import os
from dotenv import load_dotenv
from sms_alert import send_sms_alert
# Updated imports
from routing import get_fast_route, get_safe_route
from ml_engine import predict, SYNTHETIC_HOTSPOTS    

load_dotenv()

app = Flask(__name__)

# Configuration
FIREBASE_BASE = os.getenv("FIREBASE_URL")
DEVICE_ID = "handbag_001"

@app.route("/")
def home():
    return "SafeBag Backend Running (Dual Routing Enabled)"

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
        return jsonify({"error": "Firebase unreachable"}), 500

    if not data:
        return jsonify({"error": "No device data found"}), 404

    return jsonify({
        "device_id": data.get("device_id", DEVICE_ID),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "event_type": data.get("event_type", "LOCATION_CHECK"),
        "severity": data.get("severity", "LOW"),
        "gps_real": data.get("gps_real", False),
        "m_i": data.get("m_i", 0.0),
        "s_i": data.get("s_i", 0),
        "acknowledged": data.get("acknowledged", False),
        "timestamp": data.get("timestamp_ms", data.get("timestamp", ""))
    }), 200

# ---------- DUAL ROUTE API ----------
@app.route("/route", methods=["GET"])
def route_api():
    try:
        start_lat = float(request.args.get("start_lat"))
        start_lon = float(request.args.get("start_lon"))
        end_lat   = float(request.args.get("end_lat"))
        end_lon   = float(request.args.get("end_lon"))

        # Fetch both routes
        fast = get_fast_route(start_lat, start_lon, end_lat, end_lon)
        safe = get_safe_route(start_lat, start_lon, end_lat, end_lon)

        # Added GeoJSON format for GIS compatibility (Section 4.6.2)
        safe_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in safe] # GeoJSON standard uses [lon, lat]
            },
            "properties": {"route_type": "safest"}
        }

        # Return matching both Polyline and GeoJSON structures
        return jsonify({
            "fast_route": fast,
            "safe_route": safe,
            "safe_route_geojson": safe_geojson
        }), 200
    except Exception as e:
        print(f"Routing Error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------- HEATMAP DATA API ----------
@app.route("/heatmaps", methods=["GET"])
def heatmaps_api():
    try:
        # Build synthetic heatmap payload based on defined hotspots
        # Assigning an arbitrary intensity to each point for visual representation
        heatmap_data = []
        intensities = [0.9, 0.7, 0.8, 0.6] # Synthetic Risk Intensities
        for i, (lat, lon) in enumerate(SYNTHETIC_HOTSPOTS):
            weight = intensities[i] if i < len(intensities) else 0.5
            heatmap_data.append({"lat": lat, "lon": lon, "weight": weight})
            
        return jsonify({"hotspots": heatmap_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------- ML PREDICTION API ----------
@app.route("/predict", methods=["GET"])
def predict_api():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))

        # Unpack the values from updated ml_engine incorporating Eq 3.3
        risk, crime, probability, delta_hotspot, density = predict(lat, lon)
        
        return jsonify({
            "risk": risk, 
            "crime": crime,
            "safety_probability": probability,
            "delta_hotspot_km": delta_hotspot,
            "crime_density": density
        }), 200
    except Exception as e:
        print(f"ML Error: {e}")
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
        send_sms_alert(lat, lon, event_type="SOS_EMERGENCY")
        
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True, "event_type": "SOS_EMERGENCY", "s_i": 1})
        
        return jsonify({"message": "SOS Sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Fast Acknowledge ----------
@app.route('/send_ack', methods=['POST'])
def send_ack():
    try:
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True})
        return jsonify({"status": "acknowledged"}), 200
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
        # Update Firebase to stop Android polling
        patch_url = f"{FIREBASE_BASE}/latest_events/{DEVICE_ID}.json"
        requests.patch(patch_url, json={"acknowledged": True})
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)