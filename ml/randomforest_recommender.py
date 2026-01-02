# ml/randomforest_recommender.py
import numpy as np
import pandas as pd
from typing import Dict, List

class RandomForestRecommender:
    """Random Forest model for route recommendation"""
    
    def __init__(self):
        # Feature importance weights (simulating Random Forest)
        self.feature_weights = {
            'time': 0.35,
            'cost': 0.25,
            'emissions': 0.20,
            'distance': 0.10,
            'comfort': 0.10
        }
        
        self.mode_scores = {
            'driving': {'comfort': 0.8, 'reliability': 0.7},
            'transit': {'comfort': 0.6, 'reliability': 0.8},
            'walking': {'comfort': 0.4, 'reliability': 0.9},
            'bicycling': {'comfort': 0.5, 'reliability': 0.6}
        }
    
    def recommend(self, routes: List[Dict], user_preferences: Dict) -> Dict:
        """
        Recommend best route using Random Forest-like logic
        """
        if not routes:
            return None
        
        scored_routes = []
        
        for route in routes:
            score = self._calculate_score(route, user_preferences)
            route['recommendation_score'] = score
            scored_routes.append(route)
        
        # Return route with highest score
        return max(scored_routes, key=lambda x: x['recommendation_score'])
    
    def _calculate_score(self, route: Dict, preferences: Dict) -> float:
        """Calculate recommendation score"""
        # Normalize features (0-1 scale)
        max_time = 120  # 2 hours
        max_cost = 500  # ₹500
        max_emissions = 10  # 10 kg CO2
        max_distance = 50  # 50 km
        
        time_norm = 1 - min(route.get('duration', 0) / max_time, 1)
        cost_norm = 1 - min(route.get('cost', 0) / max_cost, 1)
        emissions_norm = 1 - min(route.get('emissions', 0) / max_emissions, 1)
        distance_norm = 1 - min(route.get('distance', 0) / max_distance, 1)
        
        # Get mode-specific comfort score
        mode = route.get('mode', 'driving')
        comfort = self.mode_scores.get(mode, {}).get('comfort', 0.5)
        
        # Apply user preferences
        weights = self.feature_weights.copy()
        if 'priority' in preferences:
            if preferences['priority'] == 'fastest':
                weights = {'time': 0.5, 'cost': 0.2, 'emissions': 0.2, 'distance': 0.1}
            elif preferences['priority'] == 'cheapest':
                weights = {'cost': 0.5, 'time': 0.2, 'emissions': 0.2, 'distance': 0.1}
            elif preferences['priority'] == 'greenest':
                weights = {'emissions': 0.5, 'time': 0.2, 'cost': 0.2, 'distance': 0.1}
        
        # Calculate weighted score
        score = (
            time_norm * weights['time'] +
            cost_norm * weights['cost'] +
            emissions_norm * weights['emissions'] +
            distance_norm * weights['distance'] +
            comfort * weights.get('comfort', 0)
        )
        
        return score * 100  # Convert to 0-100 scale
    
    def explain_recommendation(self, route: Dict) -> str:
        """Generate explanation for recommendation (like SHAP values)"""
        mode = route.get('mode_display', 'Unknown')
        time = route.get('duration', 0)
        cost = route.get('cost', 0)
        emissions = route.get('emissions', 0)
        score = route.get('recommendation_score', 0)
        
        explanations = [
            f"**{mode}** scored {score:.1f}/100",
            f"• Travel time: {time:.1f} minutes",
            f"• Estimated cost: ₹{cost:.0f}",
            f"• CO2 emissions: {emissions:.2f} kg"
        ]
        
        # Add mode-specific benefits
        if 'transit' in route.get('mode', ''):
            explanations.append("• Benefits: Reduces traffic congestion")
        elif 'walking' in route.get('mode', '') or 'bicycling' in route.get('mode', ''):
            explanations.append("• Benefits: Improves health, zero emissions")
        
        return "\n".join(explanations)