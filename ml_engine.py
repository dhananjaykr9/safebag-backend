import joblib
import datetime
import numpy as np
import pandas as pd
import math

# --- SPATIAL METHODOLOGY (ADDED) ---
SYNTHETIC_HOTSPOTS = [
    (21.1458, 79.0882), # Sitabuldi
    (21.1498, 79.0806), # Dharampeth
    (21.1523, 79.1001), # Mahal
    (21.1302, 79.0841), # Dhantoli
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_delta_hotspot(lat, lon):
    min_dist = float('inf')
    for h_lat, h_lon in SYNTHETIC_HOTSPOTS:
        dist = haversine(lat, lon, h_lat, h_lon)
        if dist < min_dist:
            min_dist = dist
    return round(min_dist, 3)

def calculate_crime_density(lat, lon):
    # Simulated density script: Higher if closer to multiple hotspots
    density = 0.0
    for h_lat, h_lon in SYNTHETIC_HOTSPOTS:
        dist = haversine(lat, lon, h_lat, h_lon)
        if dist < 2.0:
            density += (2.0 - dist) * 10
    return round(density, 2)

def determine_ward(lat, lon):
    # Simple spatial grid to assign a ward (1 to 10)
    grid_lat = int((lat - 21.0) * 100)
    grid_lon = int((lon - 79.0) * 100)
    ward = (grid_lat + grid_lon) % 10 + 1
    return ward
# ------------------------------------

# Load artifacts
risk_artifact = joblib.load("models/risk_model.pkl")
crime_artifact = joblib.load("models/crime_type_model.pkl")

def get_timeslot(hour):
    if 0 <= hour <= 5: return "Night"
    if 6 <= hour <= 11: return "Morning"
    if 12 <= hour <= 17: return "Afternoon"
    return "Evening"

def predict(lat, lon):
    # 1. Prepare Features (Matching Streamlit logic)
    now = datetime.datetime.now()
    hour = now.hour
    day = now.strftime("%A")
    slot = get_timeslot(hour)

    # 1.5 Calculate Spatial Methodology features (Eq 3.3)
    ward = determine_ward(lat, lon)
    delta_hotspot = calculate_delta_hotspot(lat, lon)
    density = calculate_crime_density(lat, lon)

    # transform labels if encoders exist
    le_day = risk_artifact.get("le_day")
    le_slot = risk_artifact.get("le_slot")
    
    try:
        day_enc = int(le_day.transform([day])[0]) if le_day else 0
        slot_enc = int(le_slot.transform([slot])[0]) if le_slot else 0
    except:
        day_enc = 0
        slot_enc = 0

    # Feature columns expected by model: [Ward_enc, Latitude, Longitude, Hour, DayOfWeek_enc, TimeSlot_enc]
    # We now use the pseudo-calculated ward dynamically
    print(f"Eq 3.3 Features -> {lat}, {lon}, hr:{hour}, day:{day}, ward:{ward}, d_hotspot:{delta_hotspot}, density:{density}")
    
    features = [ward, float(lat), float(lon), int(hour), day_enc, slot_enc]
    X = [features]

    # 2. Risk Prediction & Probability
    risk_model = risk_artifact["model"]
    risk_pred = risk_model.predict(X)[0]
    risk_proba = risk_model.predict_proba(X)[0]

    # Decode Risk Label
    try:
        risk_label = risk_artifact["le_risk"].inverse_transform([risk_pred])[0]
    except:
        risk_label = str(risk_pred)

    # Calculate Safety Probability (Logic: Probability of being 'Low' Risk)
    # If 'Low' isn't a specific class, we sum probabilities of non-critical classes
    classes = list(risk_model.classes_)
    safety_score = 0.5 # Default

    if "Low" in classes:
        idx = classes.index("Low")
        safety_score = float(risk_proba[idx])
    elif "Moderate" in classes:
        # Fallback: Safety = 1.0 - (High + Critical)
        high_idx = classes.index("High") if "High" in classes else -1
        crit_idx = classes.index("Critical") if "Critical" in classes else -1
        danger_prob = 0.0
        if high_idx != -1: danger_prob += risk_proba[high_idx]
        if crit_idx != -1: danger_prob += risk_proba[crit_idx]
        safety_score = 1.0 - danger_prob
    else:
        # Simple fallback if classes are numbered
        safety_score = float(np.max(risk_proba))

    # 3. Crime Prediction
    crime_model = crime_artifact["model"]
    crime_pred = crime_model.predict(X)[0]
    try:
        crime_label = crime_artifact["le_target"].inverse_transform([crime_pred])[0]
    except:
        crime_label = str(crime_pred)

    return str(risk_label), str(crime_label), float(safety_score), float(delta_hotspot), float(density)