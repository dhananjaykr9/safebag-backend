import os
import requests
import networkx as nx
import osmnx as ox
from dotenv import load_dotenv

load_dotenv()
GH_API_KEY = os.getenv("GH_API_KEY")
GRAPH_FILE = "data/nagpur_graph.graphml"

# Global cache
G_latlon = None
Gp = None

def load_graph_if_needed():
    global G_latlon, Gp
    if G_latlon is not None: 
        return

    print("Loading GraphML... this may take a moment.")
    if os.path.exists(GRAPH_FILE):
        try:
            # Load the graph
            Gp = ox.load_graphml(GRAPH_FILE)
            # Project to Lat/Lon (EPSG:4326) so coordinates are correct for the map
            G_latlon = ox.project_graph(Gp, to_crs="EPSG:4326")
            print("Graph loaded successfully.")
        except Exception as e:
            print(f"CRITICAL GRAPH ERROR: {e}")
            Gp = None
            G_latlon = None
    else:
        print(f"Graph file not found at: {GRAPH_FILE}")

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
        # Short timeout to prevent backend hanging
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if "paths" in data and len(data["paths"]) > 0:
                coords = data["paths"][0]["points"]["coordinates"]
                # GraphHopper returns [lon, lat], we need [lat, lon]
                return [[lat, lon] for lon, lat in coords]
    except Exception as e:
        print(f"GraphHopper Error: {e}")
    return []

def get_safe_route(start_lat, start_lon, end_lat, end_lon):
    """Get Safest Path via NetworkX (Green Line)"""
    load_graph_if_needed()
    
    # If graph failed to load (e.g. Memory Error on Render), return empty
    if Gp is None or G_latlon is None:
        return []

    try:
        # 1. Find the nearest graph nodes to the user's start/end points
        orig = ox.distance.nearest_nodes(G_latlon, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(G_latlon, X=end_lon, Y=end_lat)

        # 2. Calculate the path of Node IDs based on 'safety_weight'
        route_nodes = nx.shortest_path(Gp, orig, dest, weight="safety_weight")

        # 3. Extract the REAL curved road geometry
        coords = []
        
        # Iterate through pairs of nodes (u, v) in the path
        for u, v in zip(route_nodes[:-1], route_nodes[1:]):
            # Get edge data. [0] gets the first edge between these nodes
            edge_data = G_latlon.get_edge_data(u, v)[0]
            
            if "geometry" in edge_data:
                # If the road has detailed curve data, use it
                # .coords returns list of (lon, lat) tuples
                for lon, lat in edge_data["geometry"].coords:
                    coords.append([lat, lon])
            else:
                # If straight road segment, just use the node coordinates
                node_u = G_latlon.nodes[u]
                coords.append([node_u['y'], node_u['x']])

        # Append the coordinate of the final node to close the loop
        last_node = G_latlon.nodes[route_nodes[-1]]
        coords.append([last_node['y'], last_node['x']])
        
        return coords

    except Exception as e:
        print(f"Safe Route Error: {e}")
        return []
