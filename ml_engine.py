import joblib
import datetime
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import os

# --- 1. SETUP: Load Data & Models ---
try:
    risk_artifact = joblib.load("models/risk_model.pkl")
    crime_artifact = joblib.load("models/crime_type_model.pkl")
    print("✅ Models Loaded Successfully.")
except Exception as e:
    print(f"🔥 CRITICAL ERROR: Models not found. {e}")
    risk_artifact = None

# Load Ward Data for Interpolation
tree = None
ward_df = None
try:
    if os.path.exists('data/nagpur_ward_centroids.csv'):
        ward_df = pd.read_csv('data/nagpur_ward_centroids.csv')
        ward_coords = ward_df[['Latitude', 'Longitude']].values
        tree = cKDTree(ward_coords)
        print("✅ Ward Data & Spatial Tree Loaded.")
    else:
        print("⚠️ Warning: CSV not found at data/nagpur_ward_centroids.csv")
except Exception as e:
    print(f"⚠️ Error loading CSV: {e}")

# --- 2. CONFIGURATION: Safe Havens ---
SAFE_HAVENS = [
    {"name": "Sitabuldi Police Station", "lat": 21.1498, "lon": 79.0806},
    {"name": "Sadar Police Station", "lat": 21.1610, "lon": 79.0880},
    {"name": "Government Medical College", "lat": 21.1450, "lon": 79.0900},
]

def get_timeslot(hour):
    if 0 <= hour <= 5: return "Night"
    if 6 <= hour <= 11: return "Morning"
    if 12 <= hour <= 17: return "Afternoon"
    return "Evening"

def get_time_multiplier(hour):
    if 6 <= hour < 19: return 0.8   # Day (Safer)
    if 19 <= hour < 23: return 1.0  # Evening (Normal)
    return 1.5                      # Late Night (Riskier)

def is_near_safe_haven(lat, lon, threshold_km=0.2):
    for haven in SAFE_HAVENS:
        dist_deg = np.sqrt((lat - haven['lat'])**2 + (lon - haven['lon'])**2)
        if (dist_deg * 111.0) < threshold_km:
            return True, haven['name']
    return False, None

# --- 3. HELPER: Calculate Safety Probability ---
def get_safety_score_for_features(model, features, le_risk):
    """
    Robust function to get 'Safety Score' (0.0 to 1.0).
    Handles both Integer classes (0,1,2) and String classes ('Low','High').
    """
    try:
        probas = model.predict_proba([features])[0]
        classes = list(model.classes_)
        
        safe_prob = 0.0
        
        # Strategy 1: Look for explicit "Low" or "Moderate" labels
        targets = ["Low", "Moderate"]
        found = False
        
        for label in targets:
            idx = -1
            if label in classes:
                idx = classes.index(label)
            elif le_risk:
                try:
                    # Try to encode the string "Low" to the integer expected by model
                    enc_label = le_risk.transform([label])[0]
                    if enc_label in classes:
                        idx = classes.index(enc_label)
                except: pass
            
            if idx != -1:
                weight = 1.0 if label == "Low" else 0.5
                safe_prob += probas[idx] * weight
                found = True

        # Strategy 2: If we couldn't find "Low", calculate 1.0 - "Critical"
        if not found or safe_prob == 0.0:
            crit_idx = -1
            if "Critical" in classes:
                crit_idx = classes.index("Critical")
            elif le_risk:
                try:
                    enc_crit = le_risk.transform(["Critical"])[0]
                    if enc_crit in classes:
                        crit_idx = classes.index(enc_crit)
                except: pass
            
            if crit_idx != -1:
                safe_prob = 1.0 - probas[crit_idx]
            else:
                # Strategy 3: Fallback (Just take the max probability if nothing else works)
                safe_prob = np.max(probas)

        return safe_prob
    except Exception as e:
        print(f"Error calculating score: {e}")
        return 0.5 # Default to moderate if math fails

# --- 4. MAIN PREDICTION FUNCTION ---
def predict(lat, lon):
    # A. Check Safe Haven
    is_safe, haven_name = is_near_safe_haven(lat, lon)
    if is_safe:
        return "Low", "None", 0.99

    # B. Prepare Features
    now = datetime.datetime.now()
    hour = now.hour
    day = now.strftime("%A")
    slot = get_timeslot(hour)

    if risk_artifact:
        model = risk_artifact["model"]
        le_day = risk_artifact.get("le_day")
        le_slot = risk_artifact.get("le_slot")
        le_risk = risk_artifact.get("le_risk") # Vital for decoding
        
        try:
            day_enc = int(le_day.transform([day])[0]) if le_day else 0
            slot_enc = int(le_slot.transform([slot])[0]) if le_slot else 0
        except:
            day_enc, slot_enc = 0, 0
    else:
        return "Unknown", "Unknown", 0.0

    # C. Interpolation (3-Ward Average)
    if tree is not None:
        distances, indices = tree.query([lat, lon], k=3)
        weights = 1 / (distances + 0.0001)
        norm_weights = weights / np.sum(weights)
        
        total_safety = 0.0
        
        for i, idx in enumerate(indices):
            ward_enc = 0
            if 'Ward_Encoded' in ward_df.columns:
                ward_enc = ward_df.iloc[idx]['Ward_Encoded']
            
            features = [ward_enc, float(lat), float(lon), int(hour), day_enc, slot_enc]
            
            # Get score for this specific ward point
            score = get_safety_score_for_features(model, features, le_risk)
            total_safety += score * norm_weights[i]
            
        final_safety = total_safety
    else:
        # Fallback Single Point
        features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
        final_safety = get_safety_score_for_features(model, features, le_risk)

    # D. Time Adjustment
    time_mult = get_time_multiplier(hour)
    adjusted_safety = final_safety / time_mult
    adjusted_safety = max(0.0, min(1.0, adjusted_safety))

    # E. Labels
    if adjusted_safety > 0.75: risk_label = "Low"
    elif adjusted_safety > 0.40: risk_label = "Moderate"
    elif adjusted_safety > 0.20: risk_label = "High"
    else: risk_label = "Critical"

    # F. Crime Prediction
    crime_model = crime_artifact["model"]
    base_features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
    crime_pred = crime_model.predict([base_features])[0]
    try:
        crime_label = crime_artifact["le_target"].inverse_transform([crime_pred])[0]
    except:
        crime_label = str(crime_pred)

    return risk_label, crime_label, adjusted_safety
