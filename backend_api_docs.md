# Smart Safety Handbag - Backend API Documentation

This document outlines how the frontend application (mobile or web dashboard) should interact with the Python backend. It describes all the available REST API endpoints, their expected input parameters, and their JSON responses.


---

## 1. System Status
Check if the backend server is online and reachable.

**Endpoint:** `GET /status`

**Response (200 OK):**
```json
{
  "status": "Backend Running"
}
```

---

## 2. Live Device Tracking
Fetches the latest real-time GPS coordinates and event status pushed by the Smart Handbag IoT device from the Firebase Realtime Database.

**Endpoint:** `GET /location`

**Response (200 OK):**
```json
{
  "device_id": "handbag_001",
  "latitude": "21.1451",
  "longitude": "79.0885",
  "event_type": "LOCATION_CHECK", 
  "severity": "LOW",
  "m_i": 0.5,
  "s_i": 0,
  "gps_real": false,
  "acknowledged": false,
  "timestamp": "1711718000000"
}
```
*Note: `event_type` can be `LOCATION_CHECK` (normal), `PIR_MOTION` (unusual movement detected), or `SOS_EMERGENCY` (hardware double press). `severity` corresponds to LOW, MEDIUM, CRITICAL.*

---

## 3. Machine Learning Prediction Engine
Retrieves real-time context-aware safety intelligence based on the specified coordinates. This utilizes the Random Forest models and methodologies' spatial extraction features.

**Endpoint:** `GET /predict`
**Parameters:**
- `lat` (float): Latitude coordinate
- `lon` (float): Longitude coordinate

**Example Request:** `/predict?lat=21.1451&lon=79.0885`

**Response (200 OK):**
```json
{
  "crime": "Theft",
  "risk": "Low",
  "safety_probability": 0.85,
  "delta_hotspot_km": 1.25,
  "crime_density": 4.5
}
```
*Frontend Note: Use `safety_probability` to draw color-coded risk rings on the Google Map UI (e.g., Green if > 0.7, Red if < 0.4).*

---

## 4. Risk-Aware Navigation (Dual Routing)
Computes both the fastest physical path (using GraphHopper) and the safest ML-weighted path (using NetworkX Dijkstra with dynamic risk variables).

**Endpoint:** `GET /route`
**Parameters:**
- `start_lat` (float), `start_lon` (float)
- `end_lat` (float), `end_lon` (float)

**Example Request:** `/route?start_lat=21.145&start_lon=79.088&end_lat=21.150&end_lon=79.090`

**Response (200 OK):**
```json
{
  "fast_route": [
    [21.1450, 79.0880], 
    [21.1455, 79.0883]
  ],
  "safe_route": [
    [21.1450, 79.0880],
    [21.1451, 79.0881],
    [21.1455, 79.0883]
  ],
  "safe_route_geojson": {
    "type": "Feature",
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [79.0880, 21.1450],
        [79.0881, 21.1451],
        [79.0883, 21.1455]
      ]
    },
    "properties": {
      "route_type": "safest"
    }
  }
}
```
*Frontend Note: The `fast_route` and `safe_route` are arrays of `[lat, lon]` pairs for simple polylines. `safe_route_geojson` is provided in standard GeoJSON format (`[lon, lat]`) specifically requested for full GIS compatibility.*

---

## 5. Risk Heatmap Data
Returns the synthetic crime hotspots mapping required to render the Heatmap overlay around the user, fulfilling Figure 4.2 in the methodology.

**Endpoint:** `GET /heatmaps`

**Response (200 OK):**
```json
{
  "hotspots": [
    {"lat": 21.1458, "lon": 79.0882, "weight": 0.9},
    {"lat": 21.1498, "lon": 79.0806, "weight": 0.7},
    {"lat": 21.1523, "lon": 79.1001, "weight": 0.8},
    {"lat": 21.1302, "lon": 79.0841, "weight": 0.6}
  ]
}
```
*Frontend Note: Iterate through the `hotspots` array and inject them into a Google Maps Heatmap layer, using the `weight` property to set heat radius/intensity mapping.*

---

## 6. Manual SOS Trigger (Mobile App)
Allows the user to trigger a high-priority SOS emergency directly from the smartphone application. This patches the Firebase node so the hardware/backend knows an emergency is active, and dispatches Twilio SMS alerts immediately.

**Endpoint:** `POST /sos`
**Headers:** `Content-Type: application/json`

**Request Body:**
```json
{
  "latitude": 21.1451,
  "longitude": 79.0885
}
```

**Response (200 OK):**
```json
{
  "message": "SOS Sent"
}
```

---

## 7. Auto Escalation (Acknowledge)
If the dashboard operator or mobile user receives a `PIR_MOTION` alert, they can choose to actively escalate it (which disables continuous polling for that specific event and triggers emergency protocols).

**Endpoint:** `POST /escalate`
**Headers:** `Content-Type: application/json`

**Request Body:**
```json
{
  "latitude": 21.1451,
  "longitude": 79.0885,
  "event_type": "MOBILE_APP"
}
```

**Response (200 OK):**
```json
{
  "status": "success"
}
```

---

## 8. Simple Acknowledge
Silently acknowledges a pending motion alert without escalating it to a full SMS emergency state. It strictly updates the continuous UI polling flags.

**Endpoint:** `POST /send_ack`
**Headers:** `Content-Type: application/json`

**Response (200 OK):**
```json
{
  "status": "acknowledged"
}
```
