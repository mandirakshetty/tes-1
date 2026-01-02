import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from streamlit import secrets
from enum import Enum

class TransportMode(str, Enum):
    DRIVING = "driving"
    TRANSIT = "transit"
    BICYCLING = "bicycling"
    WALKING = "walking"

@dataclass
class TransportModeConfig:
    name: str
    icon: str
    google_mode: TransportMode
    eco_weight: float
    color: str
    transit_type: Optional[List[str]] = None

class Settings:
    # API Keys
    GOOGLE_MAPS_API_KEY = secrets.get("GOOGLE_MAPS_API_KEY", "")
    
    # Google Maps API Endpoints
    GOOGLE_DIRECTIONS_API = "https://maps.googleapis.com/maps/api/directions/json"
    GOOGLE_DISTANCE_MATRIX_API = "https://maps.googleapis.com/maps/api/distancematrix/json"
    GOOGLE_GEOCODING_API = "https://maps.googleapis.com/maps/api/geocode/json"
    GOOGLE_PLACES_API = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    GOOGLE_STATIC_MAPS_API = "https://maps.googleapis.com/maps/api/staticmap"
    
    # Transportation Modes Configuration
    TRANSPORT_MODES: Dict[str, TransportModeConfig] = {
        "car": TransportModeConfig(
            name="Car",
            icon="🚗",
            google_mode=TransportMode.DRIVING,
            eco_weight=0.3,
            color="#1E88E5"
        ),
        "metro": TransportModeConfig(
            name="Metro",
            icon="🚇",
            google_mode=TransportMode.TRANSIT,
            eco_weight=0.9,
            color="#8E24AA",
            transit_type=["subway"]
        ),
        "bus": TransportModeConfig(
            name="Bus",
            icon="🚌",
            google_mode=TransportMode.TRANSIT,
            eco_weight=0.7,
            color="#FB8C00",
            transit_type=["bus"]
        ),
        "bike": TransportModeConfig(
            name="Bike",
            icon="🚲",
            google_mode=TransportMode.BICYCLING,
            eco_weight=1.0,
            color="#43A047"
        ),
        "walk": TransportModeConfig(
            name="Walk",
            icon="🚶",
            google_mode=TransportMode.WALKING,
            eco_weight=1.0,
            color="#757575"
        )
    }
    
    # Map Configuration
    MAP_CENTER = (12.9716, 77.5946)  # Bangalore center
    DEFAULT_ZOOM = 12
    MAP_TILES = "OpenStreetMap"
    
    # Eco-Score Calculation Weights
    ECO_SCORE_WEIGHTS = {
        "co2_emissions": 0.40,
        "cost_efficiency": 0.25,
        "time_efficiency": 0.20,
        "mode_sustainability": 0.15
    }
    
    # Application Constants
    APP_NAME = "🌿 EcoRoute Bangalore"
    APP_TITLE = "Smart & Sustainable Route Planner"
    APP_DESCRIPTION = "Find the most eco-friendly routes across Bangalore using real-time data"
    
    # Default Parameters
    DEFAULT_TRAFFIC_MODEL = "best_guess"
    DEFAULT_TRANSIT_MODE = "bus|subway"
    DEFAULT_TRANSIT_ROUTING_PREFERENCE = "fewer_transfers"
    
    # Cost Constants (INR)
    CAR_COST_PER_KM = 10.0
    METRO_BASE_FARE = 10
    METRO_PER_KM_FARE = 2.5
    BUS_BASE_FARE = 5
    BUS_PER_KM_FARE = 1.0
    
    # Emission Constants (kg CO2 per km)
    CAR_EMISSIONS_PER_KM = 0.12
    BUS_EMISSIONS_PER_KM = 0.08
    METRO_EMISSIONS_PER_KM = 0.02
    BIKE_EMISSIONS_PER_KM = 0.0
    WALK_EMISSIONS_PER_KM = 0.0
    
    @classmethod
    def get_transit_mode_param(cls, mode: str) -> str:
        """Get transit mode parameter for Google API."""
        if mode == "metro":
            return "subway"
        elif mode == "bus":
            return "bus"
        else:
            return "bus|subway"
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km (Haversine formula)."""
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c