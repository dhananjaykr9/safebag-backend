import joblib
import datetime
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# --- 1. SETUP: Load Data & Models ---
# Load ML Models
risk_artifact = joblib.load("models/risk_model.pkl")
crime_artifact = joblib.load("models/crime_type_model.pkl")

# Load Ward Data for Interpolation (The "Knowledge Base")
# We assume this CSV exists in your 'data' folder
try:
    ward_df = pd.read_csv('data/nagpur_ward_centroids.csv')
    # Create a KDTree for fast spatial searching (Nearest Neighbors)
    ward_coords = ward_df[['Latitude', 'Longitude']].values
    tree = cKDTree(ward_coords)
    print("✅ Ward Data & Spatial Tree Loaded.")
except Exception as e:
    print(f"⚠️ Warning: Could not load ward data. Interpolation disabled. {e}")
    tree = None

# --- 2. CONFIGURATION: Heuristics ---

# List of "Safe Havens" (Police Stations, Hospitals)
# If a user is near these, safety is forced to 100%
SAFE_HAVENS = [
    {"name": "Sitabuldi Police Station", "lat": 21.1498, "lon": 79.0806},
    {"name": "Sadar Police Station", "lat": 21.1610, "lon": 79.0880},
    {"name": "Government Medical College", "lat": 21.1450, "lon": 79.0900},
    # Add more real coordinates here
]

def get_timeslot(hour):
    if 0 <= hour <= 5: return "Night"
    if 6 <= hour <= 11: return "Morning"
    if 12 <= hour <= 17: return "Afternoon"
    return "Evening"

def get_time_multiplier(hour):
    """
    Returns a risk multiplier based on hour.
    Night = Higher Risk (1.5x), Day = Lower Risk (0.8x)
    """
    if 6 <= hour < 19: return 0.8   # Day
    if 19 <= hour < 23: return 1.0  # Evening
    return 1.5                      # Late Night

def is_near_safe_haven(lat, lon, threshold_km=0.2):
    """Checks if location is within 200m of a Safe Haven"""
    for haven in SAFE_HAVENS:
        # Simple Euclidean approximation (accurate enough for short distances)
        dist_deg = np.sqrt((lat - haven['lat'])**2 + (lon - haven['lon'])**2)
        dist_km = dist_deg * 111.0 
        if dist_km < threshold_km:
            return True, haven['name']
    return False, None

# --- 3. MAIN PREDICTION ENGINE ---

def predict(lat, lon):
    # A. Check Safe Haven First (Override)
    is_safe, haven_name = is_near_safe_haven(lat, lon)
    if is_safe:
        return "Low", "None", 0.99  # 99% Safe

    # B. Prepare Basic Features
    now = datetime.datetime.now()
    hour = now.hour
    day = now.strftime("%A")
    slot = get_timeslot(hour)

    # Transform labels using loaded encoders
    le_day = risk_artifact.get("le_day")
    le_slot = risk_artifact.get("le_slot")
    try:
        day_enc = int(le_day.transform([day])[0]) if le_day else 0
        slot_enc = int(le_slot.transform([slot])[0]) if le_slot else 0
    except:
        day_enc, slot_enc = 0, 0

    # C. INTERPOLATION LOGIC (3-Ward Average)
    if tree is not None:
        # Find 3 nearest wards
        distances, indices = tree.query([lat, lon], k=3)
        
        # Calculate Weights (Inverse Distance: Closer = Higher Weight)
        # Add tiny epsilon to avoid division by zero
        weights = 1 / (distances + 0.0001)
        normalized_weights = weights / np.sum(weights)
        
        total_safety_score = 0.0
        risk_model = risk_artifact["model"]
        
        # Loop through the 3 closest wards and average their predictions
        for i, idx in enumerate(indices):
            # Get the Ward ID or Encoding from your CSV data
            # Assuming your CSV has a column 'Ward_ID_Encoded' matching training data
            # If not, we use 0, but ideally, this comes from the CSV
            ward_enc = 0 
            if 'Ward_Encoded' in ward_df.columns:
                ward_enc = ward_df.iloc[idx]['Ward_Encoded']

            features = [ward_enc, float(lat), float(lon), int(hour), day_enc, slot_enc]
            
            # Get Probability of "Low Risk" (Safety)
            probas = risk_model.predict_proba([features])[0]
            classes = list(risk_model.classes_)
            
            # Calculate a 'Safety Score' (0.0 to 1.0) for this specific ward
            ward_safety = 0.0
            if "Low" in classes:
                ward_safety = probas[classes.index("Low")]
            elif "Moderate" in classes:
                # Fallback logic if Low isn't explicit
                ward_safety = 1.0 - probas[classes.index("Critical")] if "Critical" in classes else 0.5
            
            # Add to weighted total
            total_safety_score += ward_safety * normalized_weights[i]
            
        final_safety_prob = total_safety_score

    else:
        # Fallback: No CSV data, use single point prediction
        features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
        risk_model = risk_artifact["model"]
        probas = risk_model.predict_proba([features])[0]
        # (Simplified fallback calculation)
        final_safety_prob = np.max(probas) 

    # D. Apply Time Multiplier
    # If it's late night, we penalize the safety score
    time_mult = get_time_multiplier(hour)
    
    # Logic: Higher Multiplier (Night) -> Lower Safety
    # e.g. 0.8 safety / 1.5 risk = 0.53 adjusted safety
    adjusted_safety = final_safety_prob / time_mult
    
    # Clamp between 0 and 1
    adjusted_safety = max(0.0, min(1.0, adjusted_safety))

    # E. Determine Labels based on Adjusted Score
    if adjusted_safety > 0.75:
        final_risk = "Low"
    elif adjusted_safety > 0.40:
        final_risk = "Moderate"
    elif adjusted_safety > 0.20:
        final_risk = "High"
    else:
        final_risk = "Critical"

    # F. Predict Crime Type (Using just the single point logic for simplicity)
    crime_model = crime_artifact["model"]
    base_features = [0, float(lat), float(lon), int(hour), day_enc, slot_enc]
    crime_pred = crime_model.predict([base_features])[0]
    try:
        final_crime = crime_artifact["le_target"].inverse_transform([crime_pred])[0]
    except:
        final_crime = str(crime_pred)

    return final_risk, final_crime, adjusted_safety
