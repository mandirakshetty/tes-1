# utils/route_processor.py
import streamlit as st
from typing import Dict, List
from datetime import datetime

class RouteProcessor:
    """Process and select the best routes based on practical considerations"""
    
    @staticmethod
    def get_practical_routes(routes_dict: Dict, preference: str) -> List[Dict]:
        """
        Select practical routes based on preference and real-world considerations
        """
        practical_routes = []
        
        # Define criteria based on preference
        criteria = {
            'fastest': {
                'max_walk_distance': 1.0,  # km - people won't walk too far
                'max_transfers': 2,
                'min_metro_priority': True,
                'time_weight': 0.7,
                'convenience_weight': 0.3
            },
            'cheapest': {
                'max_walk_distance': 1.5,
                'max_transfers': 3,
                'min_metro_priority': False,
                'cost_weight': 0.8,
                'time_weight': 0.2
            },
            'greenest': {
                'max_walk_distance': 2.0,
                'max_transfers': 2,
                'min_metro_priority': True,
                'emission_weight': 0.9,
                'time_weight': 0.1
            },
            'balanced': {
                'max_walk_distance': 1.2,
                'max_transfers': 2,
                'min_metro_priority': True,
                'balanced_weight': 0.5,
                'convenience_weight': 0.5
            }
        }
        
        criteria_config = criteria.get(preference, criteria['balanced'])
        
        for mode, route in routes_dict.items():
            if not route:
                continue
            
            # Check if route is practical
            if RouteProcessor._is_practical_route(route, criteria_config):
                practical_routes.append((mode, route))
        
        # Sort based on preference
        if preference == 'fastest':
            practical_routes.sort(key=lambda x: x[1]['duration_min'])
        elif preference == 'cheapest':
            practical_routes.sort(key=lambda x: RouteProcessor._estimate_cost(x[1]))
        elif preference == 'greenest':
            practical_routes.sort(key=lambda x: RouteProcessor._estimate_emissions(x[1]))
        else:  # balanced
            practical_routes.sort(key=lambda x: RouteProcessor._calculate_balance_score(x[1]))
        
        # Return as dictionary
        return {mode: route for mode, route in practical_routes}
    
    @staticmethod
    def _is_practical_route(route: Dict, criteria: Dict) -> bool:
        """Check if a route is practical for real-world use"""
        
        # Check walking distance
        total_walk_distance = 0
        if 'segments' in route:
            for segment in route['segments']:
                if segment.get('mode') == 'walk':
                    try:
                        walk_dist = float(segment['distance'].replace(' km', ''))
                        total_walk_distance += walk_dist
                    except:
                        pass
        
        if total_walk_distance > criteria['max_walk_distance']:
            return False
        
        # Check number of transfers for transit
        if route.get('actual_mode') in ['metro', 'bus']:
            transfers = RouteProcessor._count_transfers(route)
            if transfers > criteria['max_transfers']:
                return False
        
        # For metro priority in fastest/balanced/greenest
        if criteria.get('min_metro_priority', False) and route.get('actual_mode') == 'bus':
            # Only include bus if it's significantly faster/cheaper
            return route.get('duration_min', 999) < 30  # Only short bus rides
        
        return True
    
    @staticmethod
    def _count_transfers(route: Dict) -> int:
        """Count number of transfers in a transit route"""
        if 'segments' not in route:
            return 0
        
        transfers = 0
        prev_mode = None
        
        for segment in route['segments']:
            current_mode = segment.get('mode')
            if prev_mode and prev_mode != current_mode and current_mode in ['metro', 'bus']:
                transfers += 1
            prev_mode = current_mode
        
        return max(0, transfers - 1)  # Adjust for initial mode
    
    @staticmethod
    def _estimate_cost(route: Dict) -> float:
        """Estimate cost of a route"""
        distance = route.get('distance_km', 0)
        mode = route.get('actual_mode', '')
        
        # Approximate costs per km
        costs_per_km = {
            'driving': 10,  # ₹10 per km (fuel + maintenance)
            'metro': 5,     # ₹5 per km
            'bus': 2,       # ₹2 per km
            'bicycling': 0,
            'walking': 0
        }
        
        return distance * costs_per_km.get(mode, 5)
    
    @staticmethod
    def _estimate_emissions(route: Dict) -> float:
        """Estimate emissions of a route"""
        distance = route.get('distance_km', 0)
        mode = route.get('actual_mode', '')
        
        # CO2 emissions per km (kg)
        emissions_per_km = {
            'driving': 0.192,
            'metro': 0.096,
            'bus': 0.089,
            'bicycling': 0.0,
            'walking': 0.0
        }
        
        return distance * emissions_per_km.get(mode, 0.1)
    
    @staticmethod
    def _calculate_balance_score(route: Dict) -> float:
        """Calculate balanced score (time, cost, convenience)"""
        time_score = 1 / (route.get('duration_min', 1) + 1)  # +1 to avoid division by zero
        cost_score = 1 / (RouteProcessor._estimate_cost(route) + 1)
        emission_score = 1 / (RouteProcessor._estimate_emissions(route) + 0.1)
        
        # Convenience score (fewer transfers, less walking)
        convenience_score = 1
        if 'segments' in route:
            transfers = RouteProcessor._count_transfers(route)
            convenience_score *= 1 / (transfers + 1)
            
            # Check walking segments
            walk_segments = sum(1 for s in route['segments'] if s.get('mode') == 'walk')
            convenience_score *= 1 / (walk_segments + 1)
        
        return (time_score * 0.4 + cost_score * 0.3 + emission_score * 0.2 + convenience_score * 0.1)