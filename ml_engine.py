import joblib
import datetime
import numpy as np
import pandas as pd

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

    # transform labels if encoders exist
    le_day = risk_artifact.get("le_day")
    le_slot = risk_artifact.get("le_slot")
    
    try:
        day_enc = int(le_day.transform([day])[0]) if le_day else 0
        slot_enc = int(le_slot.transform([slot])[0]) if le_slot else 0
    except:
        day_enc = 0
        slot_enc = 0

    # Feature columns: [Ward_enc, Latitude, Longitude, Hour, DayOfWeek_enc, TimeSlot_enc]
    # We default Ward_enc to 0 as we don't have the shapefile logic here to detect ward
    features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
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

    return str(risk_label), str(crime_label), float(safety_score)
