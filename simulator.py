import time
import random
import requests

FIREBASE_URL = "https://smart-safety-handbag-default-rtdb.asia-southeast1.firebasedatabase.app"
DEVICE_ID = "handbag_001"

BASE_LAT = 21.1458
BASE_LON = 79.0882

def push_event(event_type="NORMAL"):
    lat = BASE_LAT
    lon = BASE_LON

    payload = {
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "event_type": event_type,
        "gps_real": False,
        "timestamp_ms": int(time.time() * 1000),
        "acknowledged": False
    }

    url = f"{FIREBASE_URL}/latest_events/{DEVICE_ID}.json"
    requests.put(url, json=payload, timeout=5)
    print(f"SENT → {event_type} @ {payload['latitude']},{payload['longitude']}")

while True:

    # continuous movement every 2 sec
    #push_event("NORMAL")
    #time.sleep(29)

    # unusual activity every ~20 sec
    if random.randint(1, 10) == 5:
        for _ in range(3):
            push_event("AUTO_UNUSUAL_ACTIVITY")
            time.sleep(10)

    # SOS every ~40 sec
    if random.randint(1, 20) == 7:
        for _ in range(5):
            push_event("USER_SOS")
            time.sleep(10)
