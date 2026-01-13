import joblib, datetime, numpy as np

risk_model = joblib.load("models/risk_model.pkl")
crime_model = joblib.load("models/crime_type_model.pkl")

def predict(lat, lon):
    now = datetime.datetime.now()
    hour = now.hour
    day_of_week = now.weekday() # 0 is Monday, 6 is Sunday
    
    # Match the feature shape exactly: [Ward, Lat, Lon, Hour, Day, Slot]
    X = [[0, float(lat), float(lon), int(hour), int(day_of_week), 0]]
    
    # Use the same logic as Streamlit to handle the dictionary structure of your .pkl
    risk_pred = risk_model["model"].predict(X)[0]
    crime_pred = crime_model["model"].predict(X)[0]
    
    # If the models use LabelEncoders, we need to decode them
    try:
        risk_label = risk_model["le_risk"].inverse_transform([risk_pred])[0]
        crime_label = crime_model["le_target"].inverse_transform([crime_pred])[0]
    except:
        risk_label = risk_pred
        crime_label = crime_pred
        
    return str(risk_label), str(crime_label)
