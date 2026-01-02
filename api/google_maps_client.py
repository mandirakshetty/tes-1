import googlemaps
import polyline as google_polyline
from datetime import datetime

class GoogleMapsClient:
    """
    Client for interacting with Google Maps APIs.
    Handles directions, distance matrix, and static maps.
    """
    
    def __init__(self, api_key):
        """Initialize the Google Maps client with the provided API key."""
        self.gmaps = googlemaps.Client(key=api_key)
        self.api_key = api_key
    
    def get_directions(self, origin, destination, mode="transit", alternatives=True):
        """
        Get detailed directions between two points.
        
        Args:
            origin (str or tuple): Starting address or (lat, lng)
            destination (str or tuple): Ending address or (lat, lng)
            mode (str): 'driving', 'walking', 'bicycling', or 'transit'
            alternatives (bool): Whether to return alternative routes
            
        Returns:
            list: List of route dictionaries from Google Directions API
        """
        try:
            # Convert tuple to string if needed
            if isinstance(origin, tuple):
                origin = f"{origin[0]},{origin[1]}"
            if isinstance(destination, tuple):
                destination = f"{destination[0]},{destination[1]}"
            
            # Request directions from Google
            directions_result = self.gmaps.directions(
                origin,
                destination,
                mode=mode,
                alternatives=alternatives,
                transit_mode=['bus', 'subway', 'train'] if mode == 'transit' else None,
                transit_routing_preference='fewer_transfers',
                departure_time=datetime.now()
            )
            
            return directions_result
            
        except Exception as e:
            print(f"Error getting directions: {e}")
            return []
    
    def decode_polyline(self, encoded_polyline):
        """
        Decode Google's encoded polyline string into a list of coordinates.
        
        Args:
            encoded_polyline (str): Encoded polyline string from Google API
            
        Returns:
            list: List of [lat, lng] coordinate pairs
        """
        if not encoded_polyline:
            return []
        
        try:
            # Decode the polyline to get coordinate list
            decoded_coords = google_polyline.decode(encoded_polyline)
            # Convert to list of [lat, lng] pairs
            return [[lat, lng] for lat, lng in decoded_coords]
        except Exception as e:
            print(f"Error decoding polyline: {e}")
            return []
    
    def get_static_map_url(self, paths, markers=None, size="600x400"):
        """
        Generate a URL for a static map with multiple paths.
        
        Args:
            paths (list): List of path dictionaries with 'coords' and 'color'
            markers (list): Optional list of marker locations
            size (str): Map dimensions in format "widthxheight"
            
        Returns:
            str: URL for the static map image
        """
        base_url = "https://maps.googleapis.com/maps/api/staticmap?"
        
        # Center the map (use first point of first path)
        if paths and paths[0]['coords']:
            center = paths[0]['coords'][0]
            map_url = f"{base_url}center={center[0]},{center[1]}&size={size}&zoom=13"
        else:
            map_url = f"{base_url}size={size}&zoom=12"
        
        # Add API key
        map_url += f"&key={self.api_key}"
        
        # Add paths to the map
        for path in paths:
            if path['coords']:
                # Encode coordinates for the path
                encoded_points = google_polyline.encode([(lat, lng) for lat, lng in path['coords']])
                map_url += f"&path=color:{path['color']}|weight:5|enc:{encoded_points}"
        
        # Add markers if provided
        if markers:
            for i, marker in enumerate(markers):
                map_url += f"&markers=color:{'red' if i==0 else 'green'}|{marker[0]},{marker[1]}"
        
        return map_url
    
    def get_distance_matrix(self, origins, destinations, mode="driving"):
        """
        Get distance matrix between multiple origins and destinations.
        
        Args:
            origins (list): List of origin addresses or coordinates
            destinations (list): List of destination addresses or coordinates
            mode (str): Travel mode
            
        Returns:
            dict: Distance matrix results
        """
        try:
            matrix = self.gmaps.distance_matrix(
                origins,
                destinations,
                mode=mode,
                departure_time=datetime.now()
            )
            return matrix
        except Exception as e:
            print(f"Error getting distance matrix: {e}")
            return None