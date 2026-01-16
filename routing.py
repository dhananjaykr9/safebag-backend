import os
import requests
import networkx as nx
import osmnx as ox
from dotenv import load_dotenv

load_dotenv()
GH_API_KEY = os.getenv("GH_API_KEY")
GRAPH_FILE = "data/nagpur_graph.graphml"

# Global cache for the graph so we don't reload it every request
G_latlon = None
Gp = None

def load_graph_if_needed():
    global G_latlon, Gp
    if G_latlon is None:
        print("Loading GraphML... this may take a moment.")
        if os.path.exists(GRAPH_FILE):
            Gp = ox.load_graphml(GRAPH_FILE)
            # Project to lat/lon for coordinate extraction
            try:
                G_latlon = ox.project_graph(Gp, to_crs="EPSG:4326")
            except:
                G_latlon = Gp # Fallback
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
    if Gp is None or G_latlon is None:
        return []

    try:
        # Find nearest nodes
        orig = ox.distance.nearest_nodes(G_latlon, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(G_latlon, X=end_lon, Y=end_lat)

        # Calculate path using 'safety_weight'
        route_nodes = nx.shortest_path(Gp, orig, dest, weight="safety_weight")

        # Extract coordinates
        coords = []
        for node_id in route_nodes:
            node = G_latlon.nodes[node_id]
            coords.append([node['y'], node['x']]) # [lat, lon]
        return coords
    except Exception as e:
        print(f"Safe Route Error: {e}")
        return []
