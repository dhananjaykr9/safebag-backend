def predict(lat, lon):
    # Example dummy ML logic for now
    if lat > 21.14:
        return "HIGH", "Robbery"
    else:
        return "LOW", "Normal"
