import os, requests
from dotenv import load_dotenv

load_dotenv()
GH_API_KEY = os.getenv("GH_API_KEY")

def get_route(start_lat, start_lon, end_lat, end_lon):
    url = "https://graphhopper.com/api/1/route"
    params = [
        ("point", f"{start_lat},{start_lon}"),
        ("point", f"{end_lat},{end_lon}"),
        ("vehicle", "car"),
        ("points_encoded", "false"),
        ("key", GH_API_KEY)
    ]
    data = requests.get(url, params=params, timeout=20).json()
    coords = data["paths"][0]["points"]["coordinates"]
    return [(lat, lon) for lon, lat in coords]
