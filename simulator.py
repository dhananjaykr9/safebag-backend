import time
import random
import requests

FIREBASE_URL = "https://smart-safety-handbag-default-rtdb.asia-southeast1.firebasedatabase.app"
DEVICE_ID = "handbag_001"

BASE_LAT = 21.1451
BASE_LON = 79.0885

def push_event(event_type="LOCATION_CHECK"):
    lat = BASE_LAT
    lon = BASE_LON

    m_i = 0.5
    s_i = 0

    severity = "LOW"
    if event_type == "PIR_MOTION":
        m_i = round(random.uniform(5.0, 9.9), 2)
        severity = "MEDIUM"
    elif event_type == "SOS_EMERGENCY":
        s_i = 1
        m_i = round(random.uniform(2.0, 8.0), 2)
        severity = "CRITICAL"

    payload = {
        "device_id": str(DEVICE_ID),
        "event_type": str(event_type),
        "latitude": str(round(lat, 6)),
        "longitude": str(round(lon, 6)),
        "timestamp": str(int(time.time() * 1000)),
        "severity": severity,
        "gps_real": False,
        "m_i": float(m_i),
        "s_i": int(s_i),
        "acknowledged": False
    }

    url = f"{FIREBASE_URL}/latest_events/{DEVICE_ID}.json"
    requests.put(url, json=payload, timeout=5)
    print(f"SENT → {event_type} @ {payload['latitude']},{payload['longitude']} | m_i={m_i}, s_i={s_i}")

while True:

    # continuous movement every 2 sec
    push_event("LOCATION_CHECK")
    time.sleep(20)

    # unusual activity every ~20 sec
    # if random.randint(1, 10) == 5:
    #     for _ in range(3):
    #         push_event("PIR_MOTION")
    #         time.sleep(20)

    # SOS every ~40 sec
    # if random.randint(1, 20) == 7:
    #     for _ in range(5):
    #         push_event("SOS_EMERGENCY")
    #         time.sleep(10)
