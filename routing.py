import os
import requests
import networkx as nx
import osmnx as ox
from dotenv import load_dotenv
from ml_engine import predict
import gc

load_dotenv()
GH_API_KEY = os.getenv("GH_API_KEY")
GRAPH_FILE = "data/nagpur_graph.graphml"

# Global cache for the graph so we don't reload it every request
G_latlon = None

def load_graph_if_needed():
    global G_latlon
    if G_latlon is None:
        print("Loading GraphML... this may take a moment.")
        if os.path.exists(GRAPH_FILE):
            G_temp = ox.load_graphml(GRAPH_FILE)
            # Project to lat/lon for coordinate extraction
            try:
                G_latlon = ox.project_graph(G_temp, to_crs="EPSG:4326")
            except Exception:
                G_latlon = G_temp # Fallback
            
            # MEMORY OPTIMIZATION for Render 512MB Limit
            # Force deletion of the duplicated initial graph from RAM
            if G_temp is not G_latlon:
                del G_temp
            gc.collect()
        else:
            print("Graph file not found! Safe routing will fail.")

def get_fast_route(start_lat, start_lon, end_lat, end_lon):
    """Get Shortest Path via GraphHopper (Blue Line)"""
    try:
        url = "https://graphhopper.com/api/1/route"
        params = [
            ("point", f"{start_lat},{start_lon}"),
            ("point", f"{end_lat},{end_lon}"),
            ("vehicle", "car"),
            ("points_encoded", "false"),
            ("key", GH_API_KEY)
        ]
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            coords = data["paths"][0]["points"]["coordinates"]
            # GraphHopper returns [lon, lat], we want [lat, lon]
            return [[lat, lon] for lon, lat in coords]
    except Exception as e:
        print(f"GraphHopper Error: {e}")
    return []

def get_safe_route(start_lat, start_lon, end_lat, end_lon):
    """Get Safest Path via NetworkX (Green Line)"""
    load_graph_if_needed()
    if G_latlon is None:
        return []

    try:
        # Find nearest nodes
        orig = ox.distance.nearest_nodes(G_latlon, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(G_latlon, X=end_lon, Y=end_lat)

        # 1. Methodology Eq 3.5 & 3.6: Dynamic ML Integration
        # We calculate the Regional ML Risk Score once using the midpoint
        # This guarantees inference runs extremely fast (latency < 30ms) as per methodology
        mid_lat = (start_lat + end_lat) / 2
        mid_lon = (start_lon + end_lon) / 2
        risk, crime, safety_prob, d_hotspot, reg_density = predict(mid_lat, mid_lon)

        ML_e = 1.0 - safety_prob # High safety_prob -> lower risk

        # Mathematical constraints from paper
        alpha = 1.0
        beta = 5.0
        gamma = 1.0
        delta = 2.0

        def dynamic_safety_cost(u, v, d):
            # D_e = physical length of segment
            D_e = float(d.get('length', 10.0))
            
            # Static crime density from edge or fallback to regional spatial density
            CD_e = float(d.get('crime_density', reg_density))
            
            # Eq 3.6: Risk Component Formulation
            R_e = (gamma * CD_e) + (delta * float(ML_e))
            
            # Eq 3.5: Composite Safety Cost Function `W_e = alpha * D_e + beta * R_e`
            # Multiplying purely R_e by D_e guarantees longer roads with identical risk add more total risk cost
            W_e = (alpha * D_e) + (beta * R_e * D_e)
            return W_e

        # Calculate path using dynamic safety function (Eq 3.7) directly on G_latlon
        route_nodes = nx.shortest_path(G_latlon, source=orig, target=dest, weight=dynamic_safety_cost)

        # Extract coordinates
        coords = []
        for node_id in route_nodes:
            node = G_latlon.nodes[node_id]
            coords.append([node['y'], node['x']]) # [lat, lon]
        return coords
    except Exception as e:
        print(f"Safe Route Error: {e}")
        return []