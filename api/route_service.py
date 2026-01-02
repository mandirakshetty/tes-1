# api/route_service.py
import googlemaps
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from utils.constants import TransportMode, RoutePriority
from calculators.eco_scorer import EcoScorer
from calculators.emission_calculator import EmissionCalculator
from calculators.cost_calculator import CostCalculator
import polyline as google_polyline

class RouteService:
    """Service for calculating and processing routes."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize route service."""
        self.api_key = api_key
        self.gmaps = googlemaps.Client(key=api_key) if api_key else None
        self.eco_scorer = EcoScorer()
        self.emission_calc = EmissionCalculator()
        self.cost_calc = CostCalculator()
        
        # Mode mapping for Google Maps
        self.mode_mapping = {
            TransportMode.CAR: "driving",
            TransportMode.METRO: "transit",
            TransportMode.BUS: "transit",
            TransportMode.WALKING: "walking",
            TransportMode.BICYCLE: "bicycling"
        }
    
    def calculate_route(self, 
                       start_coords: Tuple[float, float], 
                       end_coords: Tuple[float, float], 
                       mode: str, 
                       priority: RoutePriority) -> Optional[Dict[str, Any]]:
        """
        Calculate route for a specific mode.
        
        Args:
            start_coords: (latitude, longitude) of start point
            end_coords: (latitude, longitude) of end point
            mode: Transport mode (car, metro, bus, walking, bicycle)
            priority: Route priority (eco, fastest, cheapest, balanced)
            
        Returns:
            Route dictionary or None if calculation fails
        """
        try:
            # Convert mode string to TransportMode enum
            transport_mode = TransportMode(mode)
            
            # Get Google Maps mode
            google_mode = self.mode_mapping.get(transport_mode, "driving")
            
            # Request directions from Google Maps
            if self.gmaps:
                directions = self.gmaps.directions(
                    origin=start_coords,
                    destination=end_coords,
                    mode=google_mode,
                    alternatives=False,
                    departure_time=datetime.now(),
                    transit_mode=['bus', 'subway'] if transport_mode in [TransportMode.METRO, TransportMode.BUS] else None
                )
                
                if not directions:
                    return None
                
                route_data = directions[0]
                
                # Extract route information
                route_summary = self._extract_route_info(route_data, transport_mode)
                
                # Calculate metrics
                route_summary = self._calculate_route_metrics(
                    route_summary, 
                    transport_mode, 
                    priority
                )
                
                return route_summary
                
            else:
                # Fallback: create basic route without API
                return self._create_basic_route(
                    start_coords, end_coords, transport_mode
                )
                
        except Exception as e:
            print(f"Error calculating route: {e}")
            return None
    
    def _extract_route_info(self, 
                           route_data: Dict[str, Any], 
                           mode: TransportMode) -> Dict[str, Any]:
        """Extract route information from Google Maps response."""
        # Get first leg (there's usually only one for simple routes)
        leg = route_data['legs'][0]
        
        # Extract steps with detailed information
        steps = []
        transit_segments = []
        
        for i, step in enumerate(leg['steps']):
            step_info = {
                'step': i + 1,
                'instruction': step['html_instructions'],
                'distance': step['distance']['text'],
                'duration': step['duration']['text'],
                'mode': step['travel_mode'].lower(),
                'start_location': step['start_location'],
                'end_location': step['end_location']
            }
            
            # Extract polyline for this step
            if 'polyline' in step:
                step_info['polyline'] = step['polyline']['points']
                # Decode polyline for this step
                step_info['decoded_path'] = self._decode_polyline(
                    step['polyline']['points']
                )
            
            # Extract transit details if available
            if step['travel_mode'] == 'TRANSIT' and 'transit_details' in step:
                transit = step['transit_details']
                step_info['transit'] = {
                    'line': transit.get('line', {}).get('name', 'Unknown'),
                    'vehicle': transit.get('line', {}).get('vehicle', {}).get('type', ''),
                    'departure': transit.get('departure_stop', {}).get('name', ''),
                    'arrival': transit.get('arrival_stop', {}).get('name', ''),
                    'stops': transit.get('num_stops', 0),
                    'headsign': transit.get('headsign', '')
                }
                transit_segments.append(step_info['transit'])
            
            steps.append(step_info)
        
        # Get overall polyline
        overall_polyline = route_data.get('overview_polyline', {}).get('points', '')
        decoded_path = self._decode_polyline(overall_polyline) if overall_polyline else []
        
        return {
            'mode': mode.value,
            'start_address': leg['start_address'],
            'end_address': leg['end_address'],
            'start_location': (leg['start_location']['lat'], leg['start_location']['lng']),
            'end_location': (leg['end_location']['lat'], leg['end_location']['lng']),
            'total_distance_meters': leg['distance']['value'],
            'total_duration_seconds': leg['duration']['value'],
            'polyline': overall_polyline,
            'decoded_path': decoded_path,
            'steps': steps,
            'transit_segments': transit_segments if transit_segments else None,
            'warnings': route_data.get('warnings', []),
            'summary': route_data.get('summary', 'Route'),
            'is_realistic': True  # From Google Maps
        }
    
    def _calculate_route_metrics(self, 
                                route_summary: Dict[str, Any], 
                                mode: TransportMode,
                                priority: RoutePriority) -> Dict[str, Any]:
        """Calculate all metrics for the route."""
        # Convert distance to km
        distance_km = route_summary['total_distance_meters'] / 1000
        duration_min = route_summary['total_duration_seconds'] / 60
        
        # Calculate CO2 emissions
        emissions = self.emission_calc.calculate_co2_emissions(mode, distance_km)
        
        # Calculate cost
        cost = self.cost_calc.calculate_cost(mode, distance_km, duration_min)
        
        # Calculate eco score
        eco_score = self.eco_scorer.calculate_eco_score(
            mode=mode,
            distance_km=distance_km,
            duration_min=duration_min,
            cost_inr=cost['total_cost'],
            co2_kg=emissions['co2_kg'],
            priority=priority
        )
        
        # Add calculated metrics to route summary
        route_summary.update({
            'total_distance_km': distance_km,
            'total_duration_min': duration_min,
            'cost_inr': cost['total_cost'],
            'co2_emissions_kg': emissions['co2_kg'],
            'eco_score': eco_score,
            'emission_details': emissions,
            'cost_details': cost,
            'priority': priority.value
        })
        
        return route_summary
    
    def _create_basic_route(self, 
                           start_coords: Tuple[float, float], 
                           end_coords: Tuple[float, float], 
                           mode: TransportMode) -> Dict[str, Any]:
        """Create a basic route when API is not available."""
        # Calculate straight-line distance (simplified)
        # Using Haversine formula for distance
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lon1 = radians(start_coords[0]), radians(start_coords[1])
        lat2, lon2 = radians(end_coords[0]), radians(end_coords[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = 6371 * c  # Earth radius in km
        
        # Estimate duration based on mode
        speed_kmh = {
            TransportMode.CAR: 40,
            TransportMode.METRO: 30,
            TransportMode.BUS: 20,
            TransportMode.WALKING: 5,
            TransportMode.BICYCLE: 15
        }.get(mode, 20)
        
        duration_min = (distance_km / speed_kmh) * 60
        
        # Calculate basic metrics
        emissions = self.emission_calc.calculate_co2_emissions(mode, distance_km)
        cost = self.cost_calc.calculate_cost(mode, distance_km, duration_min)
        
        # Basic eco score
        eco_score = max(0, min(100, 
            (100 - emissions['co2_kg'] * 10) * 0.7 + 
            (100 - duration_min) * 0.2 + 
            (100 - cost['total_cost']) * 0.1
        ))
        
        return {
            'mode': mode.value,
            'start_address': f"Location at {start_coords}",
            'end_address': f"Location at {end_coords}",
            'start_location': start_coords,
            'end_location': end_coords,
            'total_distance_km': distance_km,
            'total_duration_min': duration_min,
            'cost_inr': cost['total_cost'],
            'co2_emissions_kg': emissions['co2_kg'],
            'eco_score': eco_score,
            'polyline': None,
            'decoded_path': [start_coords, end_coords],
            'steps': [
                {
                    'step': 1,
                    'instruction': f'Travel from start to destination via {mode.value}',
                    'distance': f'{distance_km:.1f} km',
                    'duration': f'{duration_min:.0f} min',
                    'mode': mode.value
                }
            ],
            'is_realistic': False,  # Not from Google Maps
            'warning': 'Using estimated route (Google Maps API not available)'
        }
    
    def _decode_polyline(self, encoded_polyline: str) -> List[Tuple[float, float]]:
        """Decode Google Maps polyline string to coordinates."""
        try:
            decoded = google_polyline.decode(encoded_polyline)
            return [(lat, lng) for lat, lng in decoded]
        except:
            return []
    
    def get_detailed_breakdown(self, route: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get detailed step-by-step breakdown of route."""
        return route.get('steps', [])
    
    def get_transit_summary(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Get transit-specific summary if route uses transit."""
        transit_segments = route.get('transit_segments', [])
        
        if not transit_segments:
            return {}
        
        total_transit_distance = 0
        total_transit_duration = 0
        
        # Calculate total transit metrics
        for segment in transit_segments:
            # This would need to extract from steps
            pass
        
        return {
            'total_transit_segments': len(transit_segments),
            'transit_segments': transit_segments,
            'transfers': max(0, len(transit_segments) - 1)
        }
    
    def compare_routes(self, routes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple routes and find best based on criteria."""
        if not routes:
            return {}
        
        comparison = {}
        for mode_str, route in routes.items():
            comparison[mode_str] = {
                'distance_km': route['total_distance_km'],
                'duration_min': route['total_duration_min'],
                'cost_inr': route['cost_inr'],
                'co2_kg': route['co2_emissions_kg'],
                'eco_score': route['eco_score']
            }
        
        # Find best for each category
        best_eco = max(routes.items(), key=lambda x: x[1]['eco_score'])
        fastest = min(routes.items(), key=lambda x: x[1]['total_duration_min'])
        cheapest = min(routes.items(), key=lambda x: x[1]['cost_inr'])
        
        return {
            'comparison': comparison,
            'best_eco': {'mode': best_eco[0], 'score': best_eco[1]['eco_score']},
            'fastest': {'mode': fastest[0], 'time': fastest[1]['total_duration_min']},
            'cheapest': {'mode': cheapest[0], 'cost': cheapest[1]['cost_inr']}
        }