import joblib
import datetime
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import os

# --- 1. SETUP: Load Data & Models ---
risk_artifact = joblib.load("models/risk_model.pkl")
crime_artifact = joblib.load("models/crime_type_model.pkl")

# Load Ward Data
tree = None
ward_df = None
try:
    if os.path.exists('data/nagpur_ward_centroids.csv'):
        ward_df = pd.read_csv('data/nagpur_ward_centroids.csv')
        ward_coords = ward_df[['Latitude', 'Longitude']].values
        tree = cKDTree(ward_coords)
        print("✅ Ward Data Loaded.")
    else:
        print("⚠️ CSV not found.")
except Exception as e:
    print(f"⚠️ Error loading CSV: {e}")

# --- 2. CONFIGURATION ---
SAFE_HAVENS = [
    {"name": "Sitabuldi Police Station", "lat": 21.1498, "lon": 79.0806},
    {"name": "Sadar Police Station", "lat": 21.1610, "lon": 79.0880},
    {"name": "General Hospital", "lat": 21.1450, "lon": 79.0900},
]

def get_timeslot(hour):
    if 0 <= hour <= 5: return "Night"
    if 6 <= hour <= 11: return "Morning"
    if 12 <= hour <= 17: return "Afternoon"
    return "Evening"

def get_time_multiplier(hour):
    if 6 <= hour < 19: return 0.8   # Day
    if 19 <= hour < 23: return 1.0  # Evening
    return 1.5                      # Late Night

def is_near_safe_haven(lat, lon, threshold_km=0.2):
    for haven in SAFE_HAVENS:
        dist_deg = np.sqrt((lat - haven['lat'])**2 + (lon - haven['lon'])**2)
        if (dist_deg * 111.0) < threshold_km:
            return True, haven['name']
    return False, None

# --- 3. HELPER: Get Probability of "Safe" ---
def get_safe_prob(model, features, le_risk):
    """
    Robustly finds the probability of being 'Low' or 'Moderate' risk.
    Handles both Integer classes (0,1,2) and String classes ('Low', 'High').
    """
    probas = model.predict_proba([features])[0]
    classes = list(model.classes_) # e.g. [0, 1, 2, 3] or ['Critical', 'High'...]
    
    safe_score = 0.0
    
    # We look for "Low" and "Moderate" to add to safety
    target_labels = ["Low", "Moderate"]
    
    for label in target_labels:
        target_idx = -1
        
        # Case A: Model uses Strings directly
        if label in classes:
            target_idx = classes.index(label)
            
        # Case B: Model uses Integers (Need LabelEncoder)
        elif le_risk:
            try:
                # Convert "Low" -> Integer (e.g., 2)
                enc_val = le_risk.transform([label])[0]
                if enc_val in classes:
                    target_idx = classes.index(enc_val)
            except:
                pass
        
        # If we found the column index, add its probability
        if target_idx != -1:
            weight = 1.0 if label == "Low" else 0.5 # Moderate adds half safety
            safe_score += probas[target_idx] * weight

    # Fallback: If score is still 0 (maybe model only predicts High/Critical?)
    # Calculate 1.0 - (Probability of Critical)
    if safe_score == 0.0:
        # Try to find "Critical" index
        crit_idx = -1
        if "Critical" in classes: 
            crit_idx = classes.index("Critical")
        elif le_risk:
            try:
                crit_val = le_risk.transform(["Critical"])[0]
                if crit_val in classes: crit_idx = classes.index(crit_val)
            except: pass
            
        if crit_idx != -1:
            safe_score = 1.0 - probas[crit_idx]
        else:
            # Last resort: just use the max prob if it's not Critical
            safe_score = 0.5 

    return safe_score

# --- 4. MAIN PREDICTION ENGINE ---
def predict(lat, lon):
    # Check Safe Haven
    is_safe, haven_name = is_near_safe_haven(lat, lon)
    if is_safe:
        return "Low", "None", 0.99

    # Prepare Features
    now = datetime.datetime.now()
    hour = now.hour
    day = now.strftime("%A")
    slot = get_timeslot(hour)

    le_day = risk_artifact.get("le_day")
    le_slot = risk_artifact.get("le_slot")
    le_risk = risk_artifact.get("le_risk") # IMPORTANT: Get Risk LabelEncoder
    
    try:
        day_enc = int(le_day.transform([day])[0]) if le_day else 0
        slot_enc = int(le_slot.transform([slot])[0]) if le_slot else 0
    except:
        day_enc, slot_enc = 0, 0

    # 3-Ward Interpolation
    if tree is not None:
        distances, indices = tree.query([lat, lon], k=3)
        weights = 1 / (distances + 0.0001)
        normalized_weights = weights / np.sum(weights)
        
        total_safety_score = 0.0
        risk_model = risk_artifact["model"]
        
        for i, idx in enumerate(indices):
            ward_enc = 0 
            if 'Ward_Encoded' in ward_df.columns:
                ward_enc = ward_df.iloc[idx]['Ward_Encoded']

            features = [ward_enc, float(lat), float(lon), int(hour), day_enc, slot_enc]
            
            # --- FIX IS HERE: Use helper to get score ---
            ward_safety = get_safe_prob(risk_model, features, le_risk)
            
            total_safety_score += ward_safety * normalized_weights[i]
            
        final_safety_prob = total_safety_score

    else:
        # Fallback (Single Point)
        features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
        risk_model = risk_artifact["model"]
        final_safety_prob = get_safe_prob(risk_model, features, le_risk)

    # Time Multiplier
    time_mult = get_time_multiplier(hour)
    adjusted_safety = final_safety_prob / time_mult
    adjusted_safety = max(0.0, min(1.0, adjusted_safety))

    # Labels
    if adjusted_safety > 0.70: final_risk = "Low"
    elif adjusted_safety > 0.40: final_risk = "Moderate"
    elif adjusted_safety > 0.20: final_risk = "High"
    else: final_risk = "Critical"

    # Crime Prediction
    crime_model = crime_artifact["model"]
    base_features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
    crime_pred = crime_model.predict([base_features])[0]
    try:
        final_crime = crime_artifact["le_target"].inverse_transform([crime_pred])[0]
    except:
        final_crime = str(crime_pred)

    return final_risk, final_crime, adjusted_safety
