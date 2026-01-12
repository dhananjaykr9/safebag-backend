import os, requests
from dotenv import load_dotenv

load_dotenv()

FIREBASE_URL = os.getenv("FIREBASE_URL")

def fetch_latest_device(device_id="handbag_001"):
    url = f"{FIREBASE_URL}/latest_events/{device_id}.json"
    r = requests.get(url, timeout=10)
    return r.json()

def fetch_events():
    url = f"{FIREBASE_URL}/events.json"
    r = requests.get(url, timeout=10)
    return r.json()
