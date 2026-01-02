"""
Main Streamlit application for Eco-Friendly Route Planner.
Complete implementation with realistic routing, cost details, and UI improvements.
"""

import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import os
from dotenv import load_dotenv
import googlemaps
import polyline as google_polyline
from math import radians, sin, cos, sqrt, atan2

# Load environment variables
load_dotenv()

# Custom classes and utilities
class TransportMode:
    """Enumeration of transport modes."""
    CAR = "car"
    METRO = "metro"
    BUS = "bus"
    WALKING = "walking"
    BICYCLE = "bicycle"
    
    @staticmethod
    def get_all():
        return [TransportMode.CAR, TransportMode.METRO, TransportMode.BUS, 
                TransportMode.WALKING, TransportMode.BICYCLE]

class RoutePriority:
    """Enumeration of route priorities."""
    ECO_FRIENDLY = "eco_friendly"
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    BALANCED = "balanced"
    
    @staticmethod
    def get_all():
        return [RoutePriority.ECO_FRIENDLY, RoutePriority.FASTEST, 
                RoutePriority.CHEAPEST, RoutePriority.BALANCED]

class Settings:
    """Application settings and configurations."""
    APP_NAME = " EcoRoute Planner"
    APP_DESCRIPTION = "Find the most eco-friendly routes across Bangalore"
    MAP_CENTER = [12.9716, 77.5946]  # Bangalore coordinates
    
    TRANSPORT_MODES = {
        "car": {
            "name": "Car",
            "icon": "🚗",
            "color": "#FF0000",
            "speed_kmh": 40,
            "cost_per_km": 8,
            "co2_per_km": 0.192
        },
        "metro": {
            "name": "Metro",
            "icon": "🚇",
            "color": "#800080",
            "speed_kmh": 35,
            "cost_per_km": 2,
            "co2_per_km": 0.035
        },
        "bus": {
            "name": "Bus",
            "icon": "🚌",
            "color": "#0000FF",
            "speed_kmh": 20,
            "cost_per_km": 1.5,
            "co2_per_km": 0.089
        },
        "walking": {
            "name": "Walking",
            "icon": "🚶",
            "color": "#FFA500",
            "speed_kmh": 5,
            "cost_per_km": 0,
            "co2_per_km": 0
        },
        "bicycle": {
            "name": "Bicycle",
            "icon": "🚴",
            "color": "#00CED1",
            "speed_kmh": 15,
            "cost_per_km": 0,
            "co2_per_km": 0
        }
    }

class GoogleMapsClient:
    """Client for Google Maps API with realistic routing."""
    
    def __init__(self, api_key: str):
        self.gmaps = googlemaps.Client(key=api_key)
        self.api_key = api_key
    
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Get coordinates from address."""
        try:
            result = self.gmaps.geocode(address)
            if result:
                location = result[0]['geometry']['location']
                return (location['lat'], location['lng'])
        except Exception as e:
            st.error(f"Geocoding error: {e}")
        return None
    
    def get_directions(self, origin: Union[str, Tuple], destination: Union[str, Tuple], 
                       mode: str, transit_modes: List[str] = None) -> List[Dict]:
        """Get detailed directions with realistic routing."""
        try:
            # Set transit modes for public transport
            transit_mode = None
            if mode == "transit":
                transit_mode = ['bus', 'subway', 'train', 'tram']
            
            directions = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                departure_time=datetime.now(),
                transit_mode=transit_mode,
                alternatives=True,
                optimize_waypoints=False
            )
            return directions
        except Exception as e:
            st.error(f"Directions error: {e}")
            return []
    
    def decode_polyline(self, encoded_polyline: str) -> List[Tuple[float, float]]:
        """Decode Google's encoded polyline to coordinates."""
        try:
            if encoded_polyline:
                decoded = google_polyline.decode(encoded_polyline)
                return [(lat, lng) for lat, lng in decoded]
        except:
            pass
        return []

class RouteService:
    """Service for calculating and processing realistic routes."""
    
    def __init__(self, google_client: GoogleMapsClient = None):
        self.google_client = google_client
        self.mode_mapping = {
            "car": "driving",
            "metro": "transit",
            "bus": "transit",
            "walking": "walking",
            "bicycle": "bicycling"
        }
    
    def calculate_route(self, start_coords: Tuple[float, float], 
                       end_coords: Tuple[float, float], 
                       mode: str, priority: str) -> Optional[Dict[str, Any]]:
        """Calculate realistic route using Google Maps API."""
        
        # If no Google client, fallback to basic calculation
        if not self.google_client:
            return self._create_basic_route(start_coords, end_coords, mode)
        
        google_mode = self.mode_mapping.get(mode, "driving")
        
        try:
            # For metro, explicitly request subway transit
            transit_modes = None
            if mode == "metro":
                transit_modes = ['subway', 'train']
            elif mode == "bus":
                transit_modes = ['bus']
            
            # Get directions from Google Maps
            directions = self.google_client.get_directions(
                origin=start_coords,
                destination=end_coords,
                mode=google_mode
            )
            
            if not directions:
                return self._create_basic_route(start_coords, end_coords, mode)
            
            route_data = directions[0]
            
            # Process route data
            processed_route = self._process_google_route(route_data, mode)
            
            # Calculate metrics
            processed_route = self._calculate_metrics(processed_route, mode, priority)
            
            return processed_route
            
        except Exception as e:
            st.error(f"Route calculation error: {e}")
            return self._create_basic_route(start_coords, end_coords, mode)
    
    def _process_google_route(self, route_data: Dict, mode: str) -> Dict[str, Any]:
        """Process Google Maps route data into standardized format."""
        leg = route_data['legs'][0]
        
        # Extract steps with detailed information
        steps = []
        transit_segments = []
        total_distance_m = 0
        total_duration_s = 0
        
        for i, step in enumerate(leg['steps']):
            step_info = {
                'step': i + 1,
                'instruction': self._clean_html_instructions(step.get('html_instructions', '')),
                'distance': step['distance']['text'],
                'distance_m': step['distance']['value'],
                'duration': step['duration']['text'],
                'duration_s': step['duration']['value'],
                'mode': step['travel_mode'].lower(),
                'start_location': step['start_location'],
                'end_location': step['end_location']
            }
            
            # Extract polyline for this step
            if 'polyline' in step:
                polyline = step['polyline']['points']
                step_info['polyline'] = polyline
                step_info['decoded_path'] = self.google_client.decode_polyline(polyline) if self.google_client else []
            
            # Extract transit details - FIXED: Properly identify metro vs bus
            if step['travel_mode'] == 'TRANSIT' and 'transit_details' in step:
                transit = step['transit_details']
                vehicle_type = transit.get('line', {}).get('vehicle', {}).get('type', '').lower()
                
                # Determine the actual mode for display
                display_mode = "transit"
                if vehicle_type == 'subway':
                    display_mode = 'metro'
                elif vehicle_type == 'bus':
                    display_mode = 'bus'
                elif vehicle_type in ['train', 'rail']:
                    display_mode = 'train'
                
                transit_info = {
                    'line': transit.get('line', {}).get('short_name', transit.get('line', {}).get('name', 'Unknown')),
                    'vehicle_type': vehicle_type,
                    'display_mode': display_mode,  # Add this for proper display
                    'departure': transit.get('departure_stop', {}).get('name', ''),
                    'arrival': transit.get('arrival_stop', {}).get('name', ''),
                    'stops': transit.get('num_stops', 0),
                    'headsign': transit.get('headsign', ''),
                    'departure_time': transit.get('departure_time', {}).get('text', ''),
                    'arrival_time': transit.get('arrival_time', {}).get('text', ''),
                    'color': transit.get('line', {}).get('color', '')
                }
                
                step_info['transit'] = transit_info
                step_info['mode'] = display_mode  # Update step mode for proper display
                transit_segments.append(transit_info)
            
            steps.append(step_info)
            total_distance_m += step['distance']['value']
            total_duration_s += step['duration']['value']
        
        # Get overall polyline
        overview_polyline = route_data.get('overview_polyline', {}).get('points', '')
        decoded_path = self.google_client.decode_polyline(overview_polyline) if self.google_client else []
        
        return {
            'mode': mode,
            'start_address': leg['start_address'],
            'end_address': leg['end_address'],
            'start_location': (leg['start_location']['lat'], leg['start_location']['lng']),
            'end_location': (leg['end_location']['lat'], leg['end_location']['lng']),
            'total_distance_m': total_distance_m,
            'total_duration_s': total_duration_s,
            'polyline': overview_polyline,
            'decoded_path': decoded_path,
            'steps': steps,
            'transit_segments': transit_segments if transit_segments else None,
            'warnings': route_data.get('warnings', []),
            'summary': route_data.get('summary', 'Route'),
            'bounds': route_data.get('bounds', {}),
            'is_realistic': True
        }
    
    def _calculate_metrics(self, route: Dict[str, Any], mode: str, priority: str) -> Dict[str, Any]:
        """Calculate all metrics for the route."""
        distance_km = route['total_distance_m'] / 1000
        duration_min = route['total_duration_s'] / 60
        
        # Get mode configuration
        mode_config = Settings.TRANSPORT_MODES.get(mode, Settings.TRANSPORT_MODES['car'])
        
        # Calculate CO2 emissions
        co2_emissions_kg = distance_km * mode_config['co2_per_km']
        
        # Calculate cost
        base_cost = distance_km * mode_config['cost_per_km']
        # Add time-based cost for some modes
        if mode == 'car':
            time_cost = (duration_min / 60) * 50  # ₹50 per hour opportunity cost
            base_cost += time_cost
        
        # Calculate eco score based on priority
        eco_score = self._calculate_eco_score(mode, distance_km, duration_min, co2_emissions_kg, base_cost, priority)
        
        # Add metrics to route
        route.update({
            'total_distance_km': round(distance_km, 2),
            'total_duration_min': round(duration_min, 1),
            'cost_inr': round(base_cost, 2),
            'co2_emissions_kg': round(co2_emissions_kg, 3),
            'eco_score': round(eco_score, 1),
            'mode_config': mode_config,
            'priority': priority
        })
        
        return route
    
    def _calculate_eco_score(self, mode: str, distance_km: float, duration_min: float, 
                            co2_kg: float, cost_inr: float, priority: str) -> float:
        """Calculate eco-friendly score (0-100)."""
        
        # Base scores by mode (higher is more eco-friendly)
        base_scores = {
            'walking': 95,
            'bicycle': 90,
            'metro': 85,
            'bus': 75,
            'car': 40
        }
        
        base_score = base_scores.get(mode, 50)
        
        # Adjust based on distance (shorter is better)
        distance_factor = 1.0
        if distance_km < 2:
            distance_factor = 1.2
        elif distance_km > 20:
            distance_factor = 0.8
        
        # Adjust based on CO2 emissions
        co2_factor = max(0.5, 1.0 - (co2_kg / 10))
        
        # Adjust based on priority
        priority_factors = {
            'eco_friendly': 1.3,
            'fastest': 0.9,
            'cheapest': 1.1,
            'balanced': 1.0
        }
        
        priority_factor = priority_factors.get(priority, 1.0)
        
        # Calculate final score
        final_score = base_score * distance_factor * co2_factor * priority_factor
        
        # Cap at 100
        return min(100, final_score)
    
    def _create_basic_route(self, start_coords: Tuple[float, float], 
                           end_coords: Tuple[float, float], mode: str) -> Dict[str, Any]:
        """Create basic route when Google Maps API is not available."""
        # Calculate distance using Haversine formula
        lat1, lon1 = radians(start_coords[0]), radians(start_coords[1])
        lat2, lon2 = radians(end_coords[0]), radians(end_coords[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = 6371 * c
        
        # Get mode configuration
        mode_config = Settings.TRANSPORT_MODES.get(mode, Settings.TRANSPORT_MODES['car'])
        
        # Estimate duration
        duration_min = (distance_km / mode_config['speed_kmh']) * 60
        
        # Calculate metrics
        co2_emissions_kg = distance_km * mode_config['co2_per_km']
        cost_inr = distance_km * mode_config['cost_per_km']
        
        # Basic eco score
        base_scores = {
            'walking': 95,
            'bicycle': 90,
            'metro': 85,
            'bus': 75,
            'car': 40
        }
        eco_score = base_scores.get(mode, 50)
        
        # Simple step
        steps = [{
            'step': 1,
            'instruction': f'Travel from start to destination via {mode}',
            'distance': f'{distance_km:.1f} km',
            'distance_m': distance_km * 1000,
            'duration': f'{duration_min:.0f} min',
            'duration_s': duration_min * 60,
            'mode': mode,
            'start_location': {'lat': start_coords[0], 'lng': start_coords[1]},
            'end_location': {'lat': end_coords[0], 'lng': end_coords[1]}
        }]
        
        return {
            'mode': mode,
            'start_address': f"Location at {start_coords[0]:.4f}, {start_coords[1]:.4f}",
            'end_address': f"Location at {end_coords[0]:.4f}, {end_coords[1]:.4f}",
            'start_location': start_coords,
            'end_location': end_coords,
            'total_distance_km': round(distance_km, 2),
            'total_duration_min': round(duration_min, 1),
            'cost_inr': round(cost_inr, 2),
            'co2_emissions_kg': round(co2_emissions_kg, 3),
            'eco_score': round(eco_score, 1),
            'polyline': None,
            'decoded_path': [start_coords, end_coords],
            'steps': steps,
            'transit_segments': None,
            'warnings': ['Using estimated route (Google Maps API not available)'],
            'summary': f'{mode.capitalize()} Route',
            'is_realistic': False,
            'mode_config': mode_config
        }
    
    def _clean_html_instructions(self, html: str) -> str:
        """Clean HTML instructions from Google Maps."""
        import re
        # Remove HTML tags
        clean = re.sub('<[^<]+?>', '', html)
        # Decode HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&')
        return clean
    
    def get_detailed_breakdown(self, route: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get detailed step-by-step breakdown of route."""
        return route.get('steps', [])
    
    def get_transit_summary(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Get transit-specific summary if route uses transit."""
        transit_segments = route.get('transit_segments', [])
        
        if not transit_segments:
            return {}
        
        total_transit_distance = sum(
            step.get('distance_m', 0) for step in route.get('steps', []) 
            if step.get('mode') in ['transit', 'metro', 'bus']
        )
        
        total_transit_duration = sum(
            step.get('duration_s', 0) for step in route.get('steps', []) 
            if step.get('mode') in ['transit', 'metro', 'bus']
        )
        
        return {
            'total_transit_segments': len(transit_segments),
            'transit_segments': transit_segments,
            'transfers': max(0, len(transit_segments) - 1),
            'total_transit_distance_km': round(total_transit_distance / 1000, 2),
            'total_transit_duration_min': round(total_transit_duration / 60, 1)
        }

class EcoScorer:
    """Calculate eco-scores and provide recommendations."""
    
    def calculate_eco_score(self, mode: str, distance_km: float, duration_min: float, 
                           cost_inr: float, co2_kg: float, priority: str) -> float:
        """Calculate eco score (simplified version)."""
        # This is a simplified version; the main calculation is in RouteService
        base_scores = {
            'walking': 95,
            'bicycle': 90,
            'metro': 85,
            'bus': 75,
            'car': 40
        }
        
        score = base_scores.get(mode, 50)
        
        # Adjust based on CO2
        if co2_kg < 0.1:
            score += 10
        elif co2_kg > 2.0:
            score -= 20
        
        # Adjust based on distance
        if distance_km < 5:
            score += 5
        
        return min(100, max(0, score))
    
    def get_recommendations(self, eco_score: float, mode: str, 
                           co2_kg: float, cost_inr: float) -> List[str]:
        """Get eco-friendly recommendations."""
        recommendations = []
        
        if eco_score >= 80:
            recommendations.append(" Excellent! You're choosing a very eco-friendly option.")
        elif eco_score >= 60:
            recommendations.append(" Good choice! You're reducing your carbon footprint.")
        else:
            recommendations.append(" Consider more eco-friendly alternatives for your next trip.")
        
        if mode == 'car' and co2_kg > 1.0:
            recommendations.append(" Consider carpooling to reduce emissions by up to 50%.")
        
        if mode in ['metro', 'bus']:
            recommendations.append(" Public transport helps reduce traffic congestion and pollution.")
        
        if eco_score < 50:
            recommendations.append(" Try walking or cycling for short distances to improve your eco-score.")
        
        return recommendations

class EmissionCalculator:
    """Calculate CO2 emissions for different transport modes."""
    
    def calculate_co2_emissions(self, mode: str, distance_km: float) -> Dict[str, float]:
        """Calculate CO2 emissions for a given mode and distance."""
        mode_config = Settings.TRANSPORT_MODES.get(mode, Settings.TRANSPORT_MODES['car'])
        co2_per_km = mode_config['co2_per_km']
        co2_kg = distance_km * co2_per_km
        
        return {
            'co2_kg': round(co2_kg, 3),
            'co2_per_km': co2_per_km,
            'distance_km': distance_km
        }
    
    def calculate_equivalent_impact(self, co2_kg: float) -> Dict[str, str]:
        """Calculate equivalent environmental impact."""
        equivalents = {
            'Tree Days': f"Equivalent to {co2_kg * 21:.0f} tree-days of CO2 absorption",
            'Smartphone Charges': f"Like charging {co2_kg * 12000:.0f} smartphones",
            'Light Bulb Hours': f"Same as {co2_kg * 400:.0f} hours of 60W bulb usage"
        }
        return equivalents

class CostCalculator:
    """Calculate costs for different transport modes."""
    
    def calculate_cost(self, mode: str, distance_km: float, duration_min: float) -> Dict[str, float]:
        """Calculate cost for a given mode, distance, and duration."""
        mode_config = Settings.TRANSPORT_MODES.get(mode, Settings.TRANSPORT_MODES['car'])
        base_cost = distance_km * mode_config['cost_per_km']
        
        # Additional costs for certain modes
        additional_costs = 0
        if mode == 'car':
            # Fuel + parking + maintenance
            additional_costs = (duration_min / 60) * 20  # ₹20 per hour opportunity cost
        
        total_cost = base_cost + additional_costs
        
        return {
            'total_cost': round(total_cost, 2),
            'base_cost': round(base_cost, 2),
            'additional_costs': round(additional_costs, 2),
            'cost_per_km': mode_config['cost_per_km']
        }

class MapRenderer:
    """Render interactive maps with realistic routes."""
    
    def __init__(self, google_api_key: str = None):
        self.google_api_key = google_api_key
        self.mode_colors = {
            'car': '#FF0000',
            'metro': '#800080',
            'bus': '#0000FF',
            'walking': '#FFA500',
            'bicycle': '#00CED1'
        }
    
    def create_route_map(self, route: Dict[str, Any], show_transit: bool = True) -> folium.Map:
        """Create a Folium map with the route."""
        # Determine map center
        if route['decoded_path']:
            center = route['decoded_path'][len(route['decoded_path']) // 2]
        else:
            center = [(route['start_location'][0] + route['end_location'][0]) / 2,
                     (route['start_location'][1] + route['end_location'][1]) / 2]
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=13,
            tiles='cartodbpositron'
        )
        
        # Add route line
        if route['decoded_path'] and len(route['decoded_path']) > 1:
            color = self.mode_colors.get(route['mode'], '#000000')
            
            folium.PolyLine(
                route['decoded_path'],
                color=color,
                weight=6,
                opacity=0.8,
                popup=f"{route['mode'].capitalize()} Route",
                tooltip=f"Click for {route['mode']} details"
            ).add_to(m)
        
        # Add markers
        folium.Marker(
            route['start_location'],
            popup=f"Start: {route['start_address']}",
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)
        
        folium.Marker(
            route['end_location'],
            popup=f"End: {route['end_address']}",
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(m)
        
        # Add transit stations if available
        if show_transit and route.get('transit_segments'):
            self._add_transit_stations(m, route['transit_segments'])
        
        return m
    
    def create_realistic_route_map(self, route: Dict[str, Any], 
                                  show_all_metro: bool = True,
                                  show_bus_routes: bool = True) -> folium.Map:
        """Create a realistic route map with detailed transit information."""
        m = self.create_route_map(route, show_transit=True)
        
        # Add detailed transit paths if available
        if route.get('steps'):
            self._add_detailed_steps(m, route['steps'])
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def _add_transit_stations(self, map_obj: folium.Map, transit_segments: List[Dict]):
        """Add transit stations to the map."""
        for segment in transit_segments:
            # This would add station markers
            # Implementation depends on available data
            pass
    
    def _add_detailed_steps(self, map_obj: folium.Map, steps: List[Dict]):
        """Add detailed step paths to the map."""
        for step in steps:
            if step.get('decoded_path') and len(step['decoded_path']) > 1:
                mode = step.get('mode', '')
                color = self.mode_colors.get(mode, '#666666')
                
                # Different styling for different modes
                if mode == 'metro':
                    weight = 8
                    dash_array = None
                    opacity = 0.9
                elif mode == 'bus':
                    weight = 6
                    dash_array = '10, 10'
                    opacity = 0.7
                elif mode == 'transit':
                    weight = 5
                    dash_array = '5, 5'
                    opacity = 0.8
                elif mode == 'walking':
                    weight = 4
                    dash_array = '2, 5'
                    opacity = 0.7
                else:
                    weight = 6
                    dash_array = None
                    opacity = 0.8
                
                folium.PolyLine(
                    step['decoded_path'],
                    color=color,
                    weight=weight,
                    opacity=opacity,
                    dash_array=dash_array,
                    popup=step.get('instruction', ''),
                    tooltip=f"{mode.capitalize()}: {step.get('distance', '')}"
                ).add_to(map_obj)
    
    def display_map(self, map_obj: folium.Map, width: int = 800, height: int = 500):
        """Display the map in Streamlit."""
        folium_static(map_obj, width=width, height=height)

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if 'routes' not in st.session_state:
        st.session_state.routes = {}
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = None
    if 'source' not in st.session_state:
        st.session_state.source = ""
    if 'destination' not in st.session_state:
        st.session_state.destination = ""
    if 'selected_modes' not in st.session_state:
        st.session_state.selected_modes = ["car", "metro", "bus"]
    if 'priority' not in st.session_state:
        st.session_state.priority = RoutePriority.BALANCED
    if 'route_calculated' not in st.session_state:
        st.session_state.route_calculated = False
    if 'start_coords' not in st.session_state:
        st.session_state.start_coords = None
    if 'end_coords' not in st.session_state:
        st.session_state.end_coords = None

# Main application
def main():
    """Main application function."""
    
    # Page configuration
    st.set_page_config(
        page_title=Settings.APP_NAME,
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2E7D32;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .eco-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 2px;
    }
    .route-step {
        padding: 12px;
        margin: 6px 0;
        border-left: 5px solid #1B5E20;
        background-color: #C8E6C9;
        border-radius: 6px;
        color: #1B5E20;
        font-weight: 500;
    }
    .transit-step {
        border-left-color: #4A148C;
        background-color: #B39DDB;
        color: #1A237E;
        font-weight: 600;
    }
    .metro-step {
        border-left-color: #800080;
        background-color: #E1BEE7;
        color: #4A148C;
        font-weight: 600;
    }
    .bus-step {
        border-left-color: #1565C0;
        background-color: #BBDEFB;
        color: #0D47A1;
        font-weight: 600;
    }
    .walk-step {
        border-left-color: #212121;
        background-color: #BDBDBD;
        color: #212121;
        font-weight: 500;
    }
    .stButton button {
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .section-header {
        padding: 10px 0;
        margin: 20px 0 10px 0;
        border-bottom: 2px solid #2E7D32;
    }
    .map-tab {
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .warning-box {
        padding: 15px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        margin: 10px 0;
    }
    .transit-detail-box {
        margin-left: 20px;
        padding: 10px;
        background: #f5f5f5;
        border-radius: 5px;
        border-left: 3px solid #4A148C;
        font-size: 13px;
        margin-top: 5px;
        margin-bottom: 10px;
    }
    .metro-detail {
        border-left-color: #800080;
        background-color: #F3E5F5;
    }
    .bus-detail {
        border-left-color: #1565C0;
        background-color: #BDBDBD;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(f"<h1 class='main-header'>{Settings.APP_NAME}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p class='sub-header'>{Settings.APP_DESCRIPTION}</p>", unsafe_allow_html=True)
    
    # Check for API key
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_API_KEY_HERE")
    has_api_key = GOOGLE_MAPS_API_KEY != "YOUR_API_KEY_HERE"
    
    if not has_api_key:
        st.markdown("""
        <div class="warning-box">
            <strong> Google Maps API key not configured.</strong><br>
            Some features may be limited. For realistic routing with actual metro/bus paths, 
            add your Google Maps API key to a <code>.env</code> file:<br>
            <code>GOOGLE_MAPS_API_KEY=your_key_here</code>
        </div>
        """, unsafe_allow_html=True)
    
    # Main layout
    col_input, col_main = st.columns([1, 2])
    
    with col_input:
        render_input_panel(has_api_key, GOOGLE_MAPS_API_KEY)
    
    with col_main:
        if st.session_state.route_calculated and st.session_state.routes:
            render_route_display(has_api_key, GOOGLE_MAPS_API_KEY)
        else:
            render_welcome_screen()

def render_input_panel(has_api_key: bool, api_key: str):
    """Render the input panel in left column."""
    st.header("Plan Your Journey")
    
    # Source input
    source = st.text_input(
        "From:",
        value=st.session_state.source,
        placeholder="Enter starting address (e.g., MG Road, Bangalore)",
        key="source_input"
    )
    
    st.session_state.source = source
    
    # Destination input
    destination = st.text_input(
        "To:",
        value=st.session_state.destination,
        placeholder="Enter destination address (e.g., Electronic City, Bangalore)",
        key="dest_input"
    )
    
    st.session_state.destination = destination
    
    # Route Preferences
    st.header("Route Preferences")
    
    priority = st.selectbox(
        "Choose priority:",
        options=RoutePriority.get_all(),
        index=RoutePriority.get_all().index(st.session_state.priority),
        key="priority_select"
    )
    st.session_state.priority = priority
    
    # Available Transport Modes
    st.header("Available Transport")
    
    # Mode selection with icons
    cols = st.columns(5)
    selected_modes = []
    
    for i, (mode_str, mode_config) in enumerate(Settings.TRANSPORT_MODES.items()):
        with cols[i % 5]:
            is_selected = st.checkbox(
                f"{mode_config['icon']} {mode_config['name']}",
                value=mode_str in st.session_state.selected_modes,
                key=f"mode_{mode_str}"
            )
            if is_selected:
                selected_modes.append(mode_str)
    
    st.session_state.selected_modes = selected_modes
    
    # API key status
    st.header("API Status")
    if has_api_key:
        st.success(" Google Maps API Key Configured")
        st.caption("Realistic routing with actual metro/bus paths enabled")
    else:
        st.error("Google Maps API Key Missing")
        st.caption("Using estimated routes without realistic paths")
    
    # Calculate button
    calculate_disabled = not (source and destination and selected_modes)
    
    if st.button(
        " Find Best Route",
        type="primary",
        use_container_width=True,
        disabled=calculate_disabled
    ):
        if calculate_disabled:
            if not source or not destination:
                st.error(" Please enter both source and destination!")
            elif not selected_modes:
                st.error(" Please select at least one transport mode!")
        else:
            with st.spinner(" Calculating routes with realistic paths..."):
                calculate_routes(source, destination, selected_modes, priority, has_api_key, api_key)

def calculate_routes(source: str, destination: str, modes: List[str], 
                    priority: str, has_api_key: bool, api_key: str):
    """Calculate routes for selected modes."""
    try:
        # Initialize services
        google_client = None
        if has_api_key:
            google_client = GoogleMapsClient(api_key)
        
        route_service = RouteService(google_client)
        
        # Get coordinates
        start_coords = None
        end_coords = None
        
        if has_api_key and google_client:
            start_coords = google_client.geocode(source)
            end_coords = google_client.geocode(destination)
        
        # Fallback coordinates if geocoding fails
        if not start_coords:
            start_coords = Settings.MAP_CENTER  # Default to Bangalore center
        if not end_coords:
            # Offset destination for demo
            end_coords = [Settings.MAP_CENTER[0] + 0.05, Settings.MAP_CENTER[1] + 0.05]
        
        # Calculate routes for each mode
        routes = {}
        for mode_str in modes:
            route = route_service.calculate_route(start_coords, end_coords, mode_str, priority)
            if route:
                routes[mode_str] = route
        
        if not routes:
            st.error(" No routes could be calculated. Please try different locations or modes.")
            return
        
        # Determine best route based on priority
        if priority == RoutePriority.ECO_FRIENDLY:
            best_mode = max(routes.items(), key=lambda x: x[1]['eco_score'])[0]
        elif priority == RoutePriority.FASTEST:
            best_mode = min(routes.items(), key=lambda x: x[1]['total_duration_min'])[0]
        elif priority == RoutePriority.CHEAPEST:
            best_mode = min(routes.items(), key=lambda x: x[1]['cost_inr'])[0]
        else:  # BALANCED
            def balanced_score(route):
                return (route['eco_score'] * 0.4 + 
                        (100 - route['total_duration_min'] / 3) * 0.3 + 
                        (100 - route['cost_inr'] / 5) * 0.3)
            
            best_mode = max(routes.items(), key=lambda x: balanced_score(x[1]))[0]
        
        # Store in session state
        st.session_state.routes = routes
        st.session_state.selected_mode = best_mode
        st.session_state.start_coords = start_coords
        st.session_state.end_coords = end_coords
        st.session_state.route_calculated = True
        
        # Show success message
        best_route = routes[best_mode]
        mode_config = Settings.TRANSPORT_MODES.get(best_mode, {})
        
        st.success(f"""
         Found {len(routes)} routes! 
        
        **Recommended: {mode_config.get('icon', '')} {mode_config.get('name', best_mode)}**
        - Distance: {best_route['total_distance_km']} km
        - Duration: {best_route['total_duration_min']} min
        - Cost: ₹{best_route['cost_inr']}
        - Eco-Score: {best_route['eco_score']}/100
        """)
        
    except Exception as e:
        st.error(f" Error calculating routes: {str(e)}")
        st.info("Please check your internet connection and try again.")

def render_welcome_screen():
    """Render welcome screen when no route is calculated."""
    
    
    # Show default map centered on Bangalore
    map_renderer = MapRenderer()
    m = folium.Map(
        location=Settings.MAP_CENTER,
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    map_renderer.display_map(m, width=800, height=400)
    
    

def render_route_display(has_api_key: bool, api_key: str):
    """Render the main route display with all details."""
    if st.session_state.selected_mode not in st.session_state.routes:
        st.error("Selected route not found. Please recalculate.")
        return
    
    route = st.session_state.routes[st.session_state.selected_mode]
    mode_config = Settings.TRANSPORT_MODES.get(route['mode'], {})
    
    # Create a container for the entire route display
    with st.container():
        # Route Header
        st.markdown(f"""
        <div class="section-header">
            <h2>{mode_config.get('icon', '')} {mode_config.get('name', route['mode'].capitalize())} Route</h2>
            <p style="color: #666; margin: 0;">
                {route['start_address']} → {route['end_address']}
                {' (Realistic Route)' if route.get('is_realistic', False) else ' (Estimated Route)'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 12px; color: #666;">DISTANCE</div>
                <div style="font-size: 24px; font-weight: bold; color: #2E7D32;">
                    {route['total_distance_km']} km
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 12px; color: #666;">DURATION</div>
                <div style="font-size: 24px; font-weight: bold; color: #2196F3;">
                    {route['total_duration_min']} min
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 12px; color: #666;">COST</div>
                <div style="font-size: 24px; font-weight: bold; color: #FF9800;">
                    ₹{route['cost_inr']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 12px; color: #666;">CO₂ EMISSIONS</div>
                <div style="font-size: 24px; font-weight: bold; color: #F44336;">
                    {route['co2_emissions_kg']} kg
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Map Display with Tabs
        st.subheader("🗺️ Route Map")
        
        map_renderer = MapRenderer(api_key if has_api_key else None)
        
        # Create tabs for different map views
        tab1, tab2, tab3 = st.tabs(["Realistic View", "Simple View", "Satellite View"])
        
        with tab1:
            st.markdown('<div class="map-tab">', unsafe_allow_html=True)
            
            if has_api_key and route.get('is_realistic', False):
                # Create realistic map
                route_map = map_renderer.create_realistic_route_map(
                    route=route,
                    show_all_metro=True,
                    show_bus_routes=(route['mode'] in ["bus", "metro"])
                )
                map_renderer.display_map(route_map, width=800, height=500)
                
                st.success(" Realistic routing using Google Maps API")
                st.caption("Metro lines show exact tracks, bus routes follow actual roads")
            else:
                # Fallback to simple map
                simple_map = map_renderer.create_route_map(route, show_transit=True)
                map_renderer.display_map(simple_map, width=800, height=500)
                
                if not has_api_key:
                    st.warning(" Google Maps API key not configured. Using simplified view.")
                    st.info("For realistic routing with actual metro/bus paths, add your Google Maps API key to `.env` file")
                else:
                    st.info(" Using estimated route. Realistic routing requires valid addresses.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown('<div class="map-tab">', unsafe_allow_html=True)
            
            # Simple view
            simple_map = map_renderer.create_route_map(route, show_transit=True)
            map_renderer.display_map(simple_map, width=800, height=500)
            
            st.caption(" Simplified route visualization")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown('<div class="map-tab">', unsafe_allow_html=True)
            
            # Satellite view
            sat_map = folium.Map(
                location=[(route['start_location'][0] + route['end_location'][0]) / 2,
                         (route['start_location'][1] + route['end_location'][1]) / 2],
                zoom_start=14,
                tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                attr="Google Satellite"
            )
            
            # Add route line
            if route['decoded_path']:
                folium.PolyLine(
                    route['decoded_path'],
                    color=mode_config.get('color', '#000000'),
                    weight=5,
                    opacity=0.8
                ).add_to(sat_map)
            
            # Add markers
            folium.Marker(
                route['start_location'],
                popup=f"Start: {route['start_address']}",
                icon=folium.Icon(color="green", icon="play")
            ).add_to(sat_map)
            
            folium.Marker(
                route['end_location'],
                popup=f"End: {route['end_address']}",
                icon=folium.Icon(color="red", icon="stop")
            ).add_to(sat_map)
            
            folium_static(sat_map, width=800, height=500)
            
            st.caption(" Satellite view with route overlay")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Route Breakdown and Eco-Score in columns
        col_details, col_eco = st.columns([2, 1])
        
        with col_details:
            st.subheader(" Route Breakdown")
            render_route_breakdown(route)
        
        with col_eco:
            st.subheader(" Eco-Score Analysis")
            render_eco_analysis(route)
        
        # Alternative Routes
        st.markdown("---")
        st.subheader(" Alternative Routes")
        render_alternative_routes()
        
        # Environmental Impact
        st.markdown("---")
        st.subheader(" Environmental Impact")
        render_environmental_impact(route)
        
        # Transit Details (if applicable)
        if route['mode'] in ["metro", "bus"] and route.get('transit_segments'):
            st.markdown("---")
            st.subheader(" Transit Details")
            render_transit_details(route)
        
        # Warnings
        if route.get('warnings'):
            st.markdown("---")
            st.subheader(" Notes")
            for warning in route['warnings']:
                st.warning(warning)

def render_route_breakdown(route: Dict[str, Any]):
    """Render the step-by-step route breakdown with proper metro/bus distinction."""
    route_service = RouteService()
    breakdown = route_service.get_detailed_breakdown(route)
    
    if not breakdown:
        st.info("No detailed breakdown available for this route.")
        return
    
    for step_info in breakdown:
        # Determine step class based on mode
        mode = step_info.get("mode", "")
        step_class = "route-step"
        
        if mode == "metro":
            step_class = "metro-step"
            icon = "🚇"
        elif mode == "bus":
            step_class = "bus-step"
            icon = "🚌"
        elif mode == "transit":
            step_class = "transit-step"
            icon = "📊"
        elif mode == "walking":
            step_class = "walk-step"
            icon = "🚶"
        else:
            icon = "🚗" if mode == "car" else "🚴" if mode == "bicycle" else "📍"
        
        st.markdown(f"""
        <div class="{step_class}">
            <div style="font-weight: bold;">Step {step_info['step']}: {icon} {step_info['instruction']}</div>
            <div style="font-size: 12px; color: #666;">
                📏 {step_info['distance']} | ⏱️ {step_info['duration']} | {mode.title()}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show transit details if available - FIXED: Proper metro/bus distinction
        if "transit" in step_info:
            transit = step_info["transit"]
            vehicle_type = transit.get('vehicle_type', '').lower()
            display_mode = transit.get('display_mode', 'transit')
            
            # Determine icon and CSS class
            if vehicle_type == 'subway' or display_mode == 'metro':
                detail_class = "transit-detail-box metro-detail"
                detail_icon = "🚇"
                transport_type = "Metro"
            elif vehicle_type == 'bus' or display_mode == 'bus':
                detail_class = "transit-detail-box bus-detail"
                detail_icon = "🚌"
                transport_type = "Bus"
            else:
                detail_class = "transit-detail-box"
                detail_icon = "📊"
                transport_type = "Transit"
            
            # Format departure and arrival times if available
            departure_time = f" at {transit.get('departure_time', '')}" if transit.get('departure_time') else ""
            arrival_time = f" at {transit.get('arrival_time', '')}" if transit.get('arrival_time') else ""
            
            st.markdown(f"""
            <div class="{detail_class}">
                <b>{detail_icon} {transport_type}: {transit.get('line', 'Unknown Line')}</b><br>
                <b>From:</b> {transit.get('departure', 'Unknown Station')}{departure_time}<br>
                <b>To:</b> {transit.get('arrival', 'Unknown Station')}{arrival_time}<br>
                <b>Stops:</b> {transit.get('stops', 0)} | <b>Headsign:</b> {transit.get('headsign', '')}
            </div>
            """, unsafe_allow_html=True)

def render_eco_analysis(route: Dict[str, Any]):
    """Render eco-score analysis."""
    eco_score = route['eco_score']
    
    # Determine color and category
    if eco_score >= 80:
        color = "#2E7D32"
        category = "Excellent "
        emoji = "🌟"
    elif eco_score >= 60:
        color = "#43A047"
        category = "Good "
        emoji = "👍"
    elif eco_score >= 40:
        color = "#FB8C00"
        category = "Moderate "
        emoji = "⚠️"
    elif eco_score >= 20:
        color = "#E53935"
        category = "Poor "
        emoji = "❌"
    else:
        color = "#B71C1C"
        category = "Very Poor "
        emoji = "⛔"
    
    # Progress bar
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>Eco-Score {emoji}</span>
            <span style="font-weight: bold; color: {color};">{eco_score:.1f}/100</span>
        </div>
        <div style="height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden;">
            <div style="height: 100%; width: {eco_score}%; background: {color}; border-radius: 10px;"></div>
        </div>
        <div style="text-align: center; margin-top: 5px; color: {color}; font-weight: bold;">
            {category}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Recommendations
    eco_scorer = EcoScorer()
    recommendations = eco_scorer.get_recommendations(
        eco_score,
        route['mode'],
        route['co2_emissions_kg'],
        route['cost_inr']
    )
    
    st.markdown("####  Recommendations")
    for rec in recommendations:
        st.info(rec)
    
    # Equivalent Impact
    emission_calc = EmissionCalculator()
    equivalents = emission_calc.calculate_equivalent_impact(route['co2_emissions_kg'])
    
    st.markdown("####  Equivalent Impact")
    for key, value in list(equivalents.items())[:2]:
        st.markdown(f"• {value}")

def render_alternative_routes():
    """Render alternative routes comparison."""
    if len(st.session_state.routes) <= 1:
        st.info("Only one mode calculated. Select more modes for comparison.")
        return
    
    # Create comparison DataFrame
    comparison_data = []
    for mode_str, alt_route in st.session_state.routes.items():
        mode_config = Settings.TRANSPORT_MODES.get(mode_str, {})
        comparison_data.append({
            "Mode": f"{mode_config.get('icon', '')} {mode_config.get('name', mode_str)}",
            "Distance (km)": alt_route['total_distance_km'],
            "Time (min)": alt_route['total_duration_min'],
            "Cost (₹)": alt_route['cost_inr'],
            "CO₂ (kg)": alt_route['co2_emissions_kg'],
            "Eco-Score": alt_route['eco_score']
        })
    
    df = pd.DataFrame(comparison_data)
    
    # Highlight selected route
    def highlight_selected(row):
        selected_mode = st.session_state.selected_mode
        mode_config = Settings.TRANSPORT_MODES.get(selected_mode, {})
        selected_name = f"{mode_config.get('icon', '')} {mode_config.get('name', selected_mode)}"
        
        if row['Mode'] == selected_name:
            return ['background-color: #e8f5e8'] * len(row)
        return [''] * len(row)
    
    # Display comparison table
    st.dataframe(
        df.style.format({
            "Distance (km)": "{:.1f}",
            "Time (min)": "{:.0f}",
            "Cost (₹)": "{:.0f}",
            "CO₂ (kg)": "{:.3f}",
            "Eco-Score": "{:.1f}"
        }).apply(highlight_selected, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    # Mode selection buttons
    st.markdown("#### Select Alternative Mode:")
    cols = st.columns(len(st.session_state.routes))
    
    for idx, (mode_str, alt_route) in enumerate(st.session_state.routes.items()):
        with cols[idx]:
            mode_config = Settings.TRANSPORT_MODES.get(mode_str, {})
            if st.button(
                f"{mode_config.get('icon', '')} {mode_config.get('name', mode_str)}",
                key=f"alt_{mode_str}",
                disabled=(mode_str == st.session_state.selected_mode),
                use_container_width=True
            ):
                st.session_state.selected_mode = mode_str
                st.rerun()

def render_environmental_impact(route: Dict[str, Any]):
    """Render environmental impact visualization."""
    col1, col2 = st.columns(2)
    
    with col1:
        # CO2 Emissions Comparison Chart
        st.markdown("####  CO₂ Emissions Comparison")
        
        # Calculate emissions for all modes for comparison
        emission_data = []
        for mode_str in Settings.TRANSPORT_MODES.keys():
            emission_calc = EmissionCalculator()
            emissions = emission_calc.calculate_co2_emissions(
                mode_str,
                route['total_distance_km']
            )
            emission_data.append({
                "Mode": Settings.TRANSPORT_MODES[mode_str]['name'],
                "CO₂ (kg)": emissions['co2_kg']
            })
        
        df_emissions = pd.DataFrame(emission_data)
        
        # Create bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_emissions["Mode"],
            y=df_emissions["CO₂ (kg)"],
            marker_color=['#2E7D32' if x == route['mode'] else '#90CAF9' 
                         for x in Settings.TRANSPORT_MODES.keys()]
        ))
        
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="CO₂ (kg)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Cost Comparison
        st.markdown("####  Cost Comparison")
        
        cost_data = []
        for mode_str in Settings.TRANSPORT_MODES.keys():
            cost_calc = CostCalculator()
            cost = cost_calc.calculate_cost(
                mode_str,
                route['total_distance_km'],
                route['total_duration_min']
            )
            cost_data.append({
                "Mode": Settings.TRANSPORT_MODES[mode_str]['name'],
                "Cost (₹)": cost['total_cost']
            })
        
        df_cost = pd.DataFrame(cost_data)
        
        # Create bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_cost["Mode"],
            y=df_cost["Cost (₹)"],
            marker_color=['#FF9800' if x == route['mode'] else '#FFCC80' 
                         for x in Settings.TRANSPORT_MODES.keys()]
        ))
        
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="Cost (₹)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_transit_details(route: Dict[str, Any]):
    """Render transit-specific details with proper metro/bus distinction."""
    route_service = RouteService()
    transit_summary = route_service.get_transit_summary(route)
    
    if not transit_summary:
        st.info("No transit details available.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Transit Segments", transit_summary.get("total_transit_segments", 0))
    
    with col2:
        distance = transit_summary.get("total_transit_distance_km", 0)
        st.metric("Transit Distance", f"{distance:.1f} km")
    
    with col3:
        st.metric("Transfers", transit_summary.get("transfers", 0))
    
    # Show transit segments with proper distinction
    if transit_summary.get("transit_segments"):
        st.markdown("####  Transit Segments:")
        
        for i, segment in enumerate(transit_summary["transit_segments"], 1):
            vehicle_type = segment.get('vehicle_type', '').lower()
            display_mode = segment.get('display_mode', 'transit')
            
            if vehicle_type == 'subway' or display_mode == 'metro':
                vehicle_icon = '🚇'
                transport_type = 'Metro'
                color = '#800080'
            elif vehicle_type == 'bus' or display_mode == 'bus':
                vehicle_icon = '🚌'
                transport_type = 'Bus'
                color = '#1565C0'
            elif vehicle_type == 'train':
                vehicle_icon = '🚂'
                transport_type = 'Train'
                color = '#008000'
            else:
                vehicle_icon = '📊'
                transport_type = 'Transit'
                color = '#666666'
            
            # Format times if available
            departure_time = f" at {segment.get('departure_time', '')}" if segment.get('departure_time') else ""
            arrival_time = f" at {segment.get('arrival_time', '')}" if segment.get('arrival_time') else ""
            
            st.markdown(f"""
            <div style="padding: 12px; margin: 8px 0; border-left: 5px solid {color}; 
                        background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1); 
                        border-radius: 6px;">
                <b>Segment {i}: {vehicle_icon} {transport_type} - {segment.get('line', 'Unknown Line')}</b><br>
                <b>Type:</b> {segment.get('vehicle_type', transport_type).title()}<br>
                <b>From:</b> {segment.get('departure', 'Unknown')}{departure_time}<br>
                <b>To:</b> {segment.get('arrival', 'Unknown')}{arrival_time}<br>
                <b>Stops:</b> {segment.get('stops', 0)} | <b>Headsign:</b> {segment.get('headsign', '')}
            </div>
            """, unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    main()