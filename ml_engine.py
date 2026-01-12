import joblib, datetime, numpy as np

risk_model = joblib.load("models/risk_model.pkl")
crime_model = joblib.load("models/crime_type_model.pkl")

def prepare_features(lat, lon):
    return [[0, lat, lon, datetime.datetime.now().hour, 0, 0]]

def predict(lat, lon):
    X = prepare_features(lat, lon)
    risk = risk_model["model"].predict(X)[0]
    crime = crime_model["model"].predict(X)[0]
    return str(risk), str(crime)
