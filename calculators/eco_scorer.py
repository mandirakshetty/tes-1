"""
Eco-score calculator for transportation routes.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math

from config.settings import Settings
from utils.constants import TransportMode, EcoScoreCategory, ECO_SCORE_THRESHOLDS, ECO_SCORE_COLORS
from calculators.emission_calculator import EmissionCalculator
from calculators.cost_calculator import CostCalculator

@dataclass
class EcoScoreComponents:
    """Components that make up the eco-score."""
    co2_score: float
    cost_score: float
    time_score: float
    mode_score: float
    health_score: float
    congestion_score: float

class EcoScorer:
    """Calculator for eco-scores of transportation routes."""
    
    def __init__(self):
        self.settings = Settings
        self.emission_calculator = EmissionCalculator()
        self.cost_calculator = CostCalculator()
    
    def calculate_eco_score(self, mode: TransportMode, distance_km: float,
                           duration_min: float, route_details: Optional[Dict] = None) -> Dict[str, any]:
        """
        Calculate comprehensive eco-score for a route.
        
        Args:
            mode: Transportation mode
            distance_km: Distance in kilometers
            duration_min: Duration in minutes
            route_details: Optional additional route details
            
        Returns:
            Dictionary with eco-score and components
        """
        # Calculate individual components
        co2_data = self.emission_calculator.calculate_co2_emissions(mode, distance_km)
        cost_data = self.cost_calculator.calculate_cost(mode, distance_km, duration_min)
        
        # Calculate component scores (0-100 scale)
        co2_score = self._calculate_co2_score(co2_data["co2_kg"], distance_km)
        cost_score = self._calculate_cost_score(cost_data["total_cost"], distance_km)
        time_score = self._calculate_time_score(duration_min, distance_km)
        mode_score = self._calculate_mode_score(mode)
        health_score = self._calculate_health_score(mode, distance_km)
        congestion_score = self._calculate_congestion_score(mode, duration_min)
        
        # Apply weights from settings
        weights = self.settings.ECO_SCORE_WEIGHTS
        
        weighted_score = (
            co2_score * weights["co2_emissions"] +
            cost_score * weights["cost_efficiency"] +
            time_score * weights["time_efficiency"] +
            mode_score * weights["mode_sustainability"]
        )
        
        # Add bonus for health benefits
        if mode in [TransportMode.BIKE, TransportMode.WALK]:
            weighted_score += health_score * 0.1
        
        # Subtract penalty for congestion contribution
        weighted_score -= congestion_score * 0.05
        
        # Normalize to 0-100 scale
        final_score = max(0, min(100, weighted_score))
        
        # Determine category
        category = self._get_eco_score_category(final_score)
        
        # Get color for category
        color = ECO_SCORE_COLORS[category]
        
        # Calculate equivalent impact
        equivalents = self.emission_calculator.calculate_equivalent_impact(co2_data["co2_kg"])
        
        # Get health benefits
        health_benefits = self.emission_calculator.calculate_health_benefits(mode, distance_km)
        
        return {
            "score": final_score,
            "category": category,
            "color": color,
            "components": EcoScoreComponents(
                co2_score=co2_score,
                cost_score=cost_score,
                time_score=time_score,
                mode_score=mode_score,
                health_score=health_score,
                congestion_score=congestion_score
            ),
            "co2_kg": co2_data["co2_kg"],
            "cost_inr": cost_data["total_cost"],
            "equivalents": equivalents,
            "health_benefits": health_benefits,
            "details": {
                "distance_km": distance_km,
                "duration_min": duration_min,
                "mode": mode.value
            }
        }
    
    def _calculate_co2_score(self, co2_kg: float, distance_km: float) -> float:
        """Calculate CO2 score (lower emissions = higher score)."""
        # Target: 0.05 kg CO2 per km is excellent (electric public transport)
        # Maximum: 0.2 kg CO2 per km is poor (single occupancy car)
        
        co2_per_km = co2_kg / distance_km if distance_km > 0 else 0
        
        if co2_per_km <= 0.02:  # Walking, cycling
            return 100
        elif co2_per_km <= 0.05:  # Electric metro
            return 90
        elif co2_per_km <= 0.08:  # Bus
            return 75
        elif co2_per_km <= 0.12:  # Carpool
            return 50
        elif co2_per_km <= 0.15:  # Single occupancy car
            return 25
        else:  # Large vehicles, inefficient cars
            return 10
    
    def _calculate_cost_score(self, cost_inr: float, distance_km: float) -> float:
        """Calculate cost efficiency score (lower cost = higher score)."""
        cost_per_km = cost_inr / distance_km if distance_km > 0 else 0
        
        if cost_per_km <= 1:  # Walking, cycling
            return 100
        elif cost_per_km <= 3:  # Bus
            return 85
        elif cost_per_km <= 5:  # Metro
            return 70
        elif cost_per_km <= 10:  # Carpool
            return 50
        elif cost_per_km <= 15:  # Ride-sharing
            return 30
        else:  # Taxi, premium services
            return 15
    
    def _calculate_time_score(self, duration_min: float, distance_km: float) -> float:
        """Calculate time efficiency score."""
        speed_kmh = (distance_km / (duration_min / 60)) if duration_min > 0 else 0
        
        # In urban context, moderate speed is optimal
        # Too fast means likely car (less eco-friendly)
        # Too slow means walking for long distances (less practical)
        
        if 15 <= speed_kmh <= 25:  # Optimal range (bus, metro, bike)
            return 80
        elif 25 < speed_kmh <= 40:  # Car in traffic
            return 60
        elif speed_kmh > 40:  # Car on highway
            return 40
        elif 5 <= speed_kmh < 15:  # Bike, slow traffic
            return 70
        else:  # Walking
            return 90  # Walking gets high score for short distances
    
    def _calculate_mode_score(self, mode: TransportMode) -> float:
        """Calculate mode sustainability score."""
        mode_config = self.settings.TRANSPORT_MODES[mode]
        return mode_config.eco_weight * 100
    
    def _calculate_health_score(self, mode: TransportMode, distance_km: float) -> float:
        """Calculate health benefit score."""
        if mode == TransportMode.WALK:
            return min(100, distance_km * 20)  # 5km walk = 100 score
        elif mode == TransportMode.BIKE:
            return min(100, distance_km * 15)  # ~7km bike = 100 score
        elif mode == TransportMode.METRO:
            # Includes walking to/from stations
            walking_distance = min(2, distance_km * 0.2)  # Assume 20% walking
            return min(50, walking_distance * 20)
        elif mode == TransportMode.BUS:
            walking_distance = min(1, distance_km * 0.1)  # Assume 10% walking
            return min(30, walking_distance * 20)
        else:  # Car
            return 0
    
    def _calculate_congestion_score(self, mode: TransportMode, duration_min: float) -> float:
        """Calculate congestion contribution score (lower is better)."""
        # How much does this mode contribute to traffic congestion
        if mode == TransportMode.CAR:
            # Cars contribute most to congestion
            return min(100, duration_min * 0.5)  # 30 min drive = 15 score
        elif mode == TransportMode.BUS:
            # Buses can cause congestion but carry many people
            return min(50, duration_min * 0.2)
        elif mode == TransportMode.METRO:
            # Metro doesn't contribute to road congestion
            return 0
        else:  # Bike, Walk
            # Active modes reduce congestion
            return -20  # Negative score = reduces congestion
    
    def _get_eco_score_category(self, score: float) -> EcoScoreCategory:
        """Get eco-score category based on score."""
        if score >= ECO_SCORE_THRESHOLDS[EcoScoreCategory.EXCELLENT]:
            return EcoScoreCategory.EXCELLENT
        elif score >= ECO_SCORE_THRESHOLDS[EcoScoreCategory.GOOD]:
            return EcoScoreCategory.GOOD
        elif score >= ECO_SCORE_THRESHOLDS[EcoScoreCategory.MODERATE]:
            return EcoScoreCategory.MODERATE
        elif score >= ECO_SCORE_THRESHOLDS[EcoScoreCategory.POOR]:
            return EcoScoreCategory.POOR
        else:
            return EcoScoreCategory.VERY_POOR
    
    def get_recommendations(self, score: float, mode: TransportMode, 
                           co2_kg: float, cost_inr: float) -> List[str]:
        """Get personalized recommendations based on eco-score."""
        recommendations = []
        
        if score >= 80:
            recommendations.append("🎉 Excellent choice! You're making a significant positive impact.")
            recommendations.append("Consider sharing this route with friends to spread eco-awareness.")
        elif score >= 60:
            recommendations.append("👍 Good choice! You're being environmentally conscious.")
            recommendations.append("For even better scores, try combining with walking for short distances.")
        elif score >= 40:
            recommendations.append("💡 There's room for improvement.")
            recommendations.append(f"Consider {self._get_better_mode(mode)} for a better eco-score.")
        else:
            recommendations.append("🌍 Consider more eco-friendly alternatives.")
            recommendations.append(f"{self._get_best_alternative(mode)} would significantly reduce your environmental impact.")
        
        # CO2 specific recommendations
        if co2_kg > 5:
            recommendations.append(f"🌳 Your trip emits {co2_kg:.1f}kg CO2. That's equivalent to what a tree absorbs in {co2_kg/21:.1f} months.")
        
        # Cost specific recommendations
        if cost_inr > 200 and mode == TransportMode.CAR:
            recommendations.append(f"💰 You could save ₹{cost_inr * 0.7:.0f} by using public transport for this trip.")
        
        # Mode-specific recommendations
        if mode == TransportMode.CAR:
            recommendations.append("🚗💨 Consider carpooling to reduce emissions and costs.")
        elif mode == TransportMode.METRO:
            recommendations.append("🚇👍 Metro is one of the most efficient ways to travel in Bangalore.")
        elif mode == TransportMode.BUS:
            recommendations.append("🚌 BMTC buses are affordable and reduce road congestion.")
        
        return recommendations
    
    def _get_better_mode(self, current_mode: TransportMode) -> str:
        """Suggest a better transportation mode."""
        if current_mode == TransportMode.CAR:
            return "metro or bus"
        elif current_mode == TransportMode.BUS:
            return "metro for faster travel"
        elif current_mode == TransportMode.METRO:
            return "walking or cycling for short distances"
        else:
            return "continue your current mode"
    
    def _get_best_alternative(self, current_mode: TransportMode) -> str:
        """Suggest the best alternative transportation mode."""
        if current_mode == TransportMode.CAR:
            return "Taking metro or bus"
        elif current_mode in [TransportMode.BUS, TransportMode.METRO]:
            return "Walking or cycling for portions of your journey"
        else:
            return "Your current mode is already excellent"
    
    def compare_modes(self, distance_km: float, duration_by_mode: Dict[TransportMode, float]) -> Dict[str, Dict]:
        """
        Compare eco-scores across multiple modes.
        
        Args:
            distance_km: Distance in kilometers
            duration_by_mode: Dictionary of durations by mode
            
        Returns:
            Dictionary with eco-scores for each mode
        """
        comparison = {}
        
        for mode, duration_min in duration_by_mode.items():
            eco_data = self.calculate_eco_score(mode, distance_km, duration_min)
            comparison[mode.value] = {
                "score": eco_data["score"],
                "category": eco_data["category"],
                "co2_kg": eco_data["co2_kg"],
                "cost_inr": eco_data["cost_inr"],
                "color": eco_data["color"]
            }
        
        # Sort by eco-score (descending)
        sorted_comparison = dict(sorted(
            comparison.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        ))
        
        return sorted_comparison
    
    def calculate_aggregate_impact(self, trips: List[Dict]) -> Dict[str, any]:
        """
        Calculate aggregate environmental impact for multiple trips.
        
        Args:
            trips: List of trip dictionaries with mode, distance, duration
            
        Returns:
            Aggregate impact data
        """
        total_co2 = 0
        total_cost = 0
        total_distance = 0
        total_duration = 0
        mode_counts = {}
        
        for trip in trips:
            mode = TransportMode(trip["mode"])
            distance = trip["distance"]
            duration = trip["duration"]
            
            eco_data = self.calculate_eco_score(mode, distance, duration)
            
            total_co2 += eco_data["co2_kg"]
            total_cost += eco_data["cost_inr"]
            total_distance += distance
            total_duration += duration
            
            # Count modes
            mode_counts[mode.value] = mode_counts.get(mode.value, 0) + 1
        
        # Calculate averages
        avg_co2_per_km = total_co2 / total_distance if total_distance > 0 else 0
        avg_cost_per_km = total_cost / total_distance if total_distance > 0 else 0
        
        # Calculate overall eco-score
        avg_speed = (total_distance / (total_duration / 60)) if total_duration > 0 else 0
        avg_eco_score = self.calculate_eco_score(
            self._get_most_common_mode(mode_counts),
            total_distance,
            total_duration
        )["score"]
        
        return {
            "total_co2_kg": total_co2,
            "total_cost_inr": total_cost,
            "total_distance_km": total_distance,
            "total_duration_min": total_duration,
            "avg_co2_per_km": avg_co2_per_km,
            "avg_cost_per_km": avg_cost_per_km,
            "avg_speed_kmh": avg_speed,
            "overall_eco_score": avg_eco_score,
            "mode_distribution": mode_counts,
            "equivalents": self.emission_calculator.calculate_equivalent_impact(total_co2)
        }
    
    def _get_most_common_mode(self, mode_counts: Dict[str, int]) -> TransportMode:
        """Get the most commonly used transportation mode."""
        if not mode_counts:
            return TransportMode.WALK
        
        most_common = max(mode_counts.items(), key=lambda x: x[1])[0]
        return TransportMode(most_common)