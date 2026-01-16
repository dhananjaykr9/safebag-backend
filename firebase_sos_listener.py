import requests
import time
import os
from dotenv import load_dotenv
from sms_alert import send_sms_alert

load_dotenv()

FIREBASE_URL = os.getenv("FIREBASE_URL")

CHECK_INTERVAL = 4  # seconds
PROCESSED = set()

def listen_sos():
    print("🔥 Firebase SOS Listener started...")
    while True:
        try:
            r = requests.get(f"{FIREBASE_URL}/events.json", timeout=10)
            data = r.json() if r.ok else {}

            for key, ev in (data or {}).items():
                if key in PROCESSED:
                    continue
                if not isinstance(ev, dict):
                    continue

                event_type = ev.get("event_type")
                if event_type not in ["USER_SOS", "AUTO_UNUSUAL_ACTIVITY"]:
                    continue

                lat = ev.get("latitude")
                lon = ev.get("longitude")

                if lat and lon:
                    print(f"🚨 SOS detected → sending SMS: {lat},{lon}")
                    send_sms_alert(lat, lon, event_type)
                    PROCESSED.add(key)

        except Exception as e:
            print("Listener error:", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    listen_sos()
