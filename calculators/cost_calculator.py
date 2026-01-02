"""
Cost calculator for different transportation modes.
"""

from typing import Dict, Optional
from datetime import datetime
import math

from config.settings import Settings
from utils.constants import TransportMode

class CostCalculator:
    """Calculator for transportation costs."""
    
    def __init__(self):
        self.settings = Settings
    
    def calculate_cost(self, mode: TransportMode, distance_km: float,
                      duration_min: float, time_of_day: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate cost for a trip.
        
        Args:
            mode: Transportation mode
            distance_km: Distance in kilometers
            duration_min: Duration in minutes
            time_of_day: Optional time of day for dynamic pricing
            
        Returns:
            Dictionary with cost breakdown
        """
        if mode == TransportMode.CAR:
            return self._calculate_car_cost(distance_km, duration_min, time_of_day)
        elif mode == TransportMode.METRO:
            return self._calculate_metro_cost(distance_km)
        elif mode == TransportMode.BUS:
            return self._calculate_bus_cost(distance_km)
        elif mode == TransportMode.BIKE:
            return self._calculate_bike_cost(distance_km, duration_min)
        elif mode == TransportMode.WALK:
            return self._calculate_walk_cost(distance_km)
        else:
            # Default calculation using settings
            mode_config = self.settings.TRANSPORT_MODES[mode.value]
            cost = distance_km * self._get_cost_per_km(mode)
            return {
                "total_cost": cost,
                "cost_per_km": self._get_cost_per_km(mode),
                "method": "default"
            }
    
    def _calculate_car_cost(self, distance_km: float, duration_min: float,
                           time_of_day: Optional[str] = None) -> Dict[str, float]:
        """Calculate car trip cost."""
        # Fuel cost
        fuel_efficiency = 15  # km per liter (Bangalore average)
        fuel_price = 100  # INR per liter (petrol)
        fuel_cost = (distance_km / fuel_efficiency) * fuel_price
        
        # Maintenance cost (per km)
        maintenance_cost_per_km = 3.0  # INR per km
        maintenance_cost = distance_km * maintenance_cost_per_km
        
        # Parking cost (if applicable)
        parking_cost = self._estimate_parking_cost(duration_min, time_of_day)
        
        # Toll charges (if applicable)
        toll_cost = self._estimate_toll_charges(distance_km)
        
        # Depreciation
        depreciation_per_km = 2.0  # INR per km
        depreciation_cost = distance_km * depreciation_per_km
        
        total_cost = fuel_cost + maintenance_cost + parking_cost + toll_cost + depreciation_cost
        
        return {
            "total_cost": total_cost,
            "fuel_cost": fuel_cost,
            "maintenance_cost": maintenance_cost,
            "parking_cost": parking_cost,
            "toll_cost": toll_cost,
            "depreciation_cost": depreciation_cost,
            "cost_per_km": total_cost / distance_km if distance_km > 0 else 0,
            "method": "detailed_car"
        }
    
    def _calculate_metro_cost(self, distance_km: float) -> Dict[str, float]:
        """Calculate metro fare."""
        # Bangalore metro fare structure
        base_fare = Settings.METRO_BASE_FARE  # INR
        per_km_fare = Settings.METRO_PER_KM_FARE  # INR per km
        
        fare = base_fare + (distance_km * per_km_fare)
        
        # Cap at maximum fare
        max_fare = 60  # INR
        fare = min(fare, max_fare)
        
        return {
            "total_cost": fare,
            "base_fare": base_fare,
            "distance_fare": distance_km * per_km_fare,
            "cost_per_km": fare / distance_km if distance_km > 0 else 0,
            "method": "metro_fare"
        }
    
    def _calculate_bus_cost(self, distance_km: float) -> Dict[str, float]:
        """Calculate bus fare."""
        # BMTC fare structure
        base_fare = Settings.BUS_BASE_FARE
        per_km_fare = Settings.BUS_PER_KM_FARE
        
        if distance_km <= 2:
            fare = 5
        elif distance_km <= 4:
            fare = 10
        elif distance_km <= 6:
            fare = 15
        elif distance_km <= 10:
            fare = 25
        elif distance_km <= 15:
            fare = 30
        else:
            fare = 35
        
        # Additional for AC buses
        ac_surcharge = 10  # INR
        
        total_fare = fare + ac_surcharge
        
        return {
            "total_cost": total_fare,
            "base_fare": fare,
            "ac_surcharge": ac_surcharge,
            "cost_per_km": total_fare / distance_km if distance_km > 0 else 0,
            "method": "bus_fare"
        }
    
    def _calculate_bike_cost(self, distance_km: float, duration_min: float) -> Dict[str, float]:
        """Calculate bike trip cost."""
        # For personal bike
        maintenance_per_km = 0.5  # INR per km
        maintenance_cost = distance_km * maintenance_per_km
        
        # For rental bike (example)
        rental_rate_per_min = 1.0  # INR per minute
        rental_cost = duration_min * rental_rate_per_min
        
        # Choose the lower cost option
        total_cost = min(maintenance_cost, rental_cost)
        method = "rental" if rental_cost < maintenance_cost else "personal"
        
        return {
            "total_cost": total_cost,
            "maintenance_cost": maintenance_cost,
            "rental_cost": rental_cost,
            "cost_per_km": total_cost / distance_km if distance_km > 0 else 0,
            "method": f"bike_{method}"
        }
    
    def _calculate_walk_cost(self, distance_km: float) -> Dict[str, float]:
        """Calculate walking cost (essentially free)."""
        # Only consider if we want to account for shoe wear or time value
        shoe_wear_per_km = 0.1  # INR per km (very rough estimate)
        shoe_cost = distance_km * shoe_wear_per_km
        
        return {
            "total_cost": shoe_cost,
            "shoe_wear_cost": shoe_cost,
            "cost_per_km": shoe_wear_per_km,
            "method": "walking"
        }
    
    def _get_cost_per_km(self, mode: TransportMode) -> float:
        """Get cost per km for a transportation mode."""
        if mode == TransportMode.CAR:
            return Settings.CAR_COST_PER_KM
        elif mode == TransportMode.METRO:
            return Settings.METRO_PER_KM_FARE
        elif mode == TransportMode.BUS:
            return Settings.BUS_PER_KM_FARE
        else:
            return 0.0
    
    def _estimate_parking_cost(self, duration_min: float, time_of_day: Optional[str] = None) -> float:
        """Estimate parking cost."""
        # Bangalore parking rates
        if time_of_day in ["peak", None]:  # Default to peak hours
            rate_per_hour = 30  # INR per hour
        else:
            rate_per_hour = 20  # INR per hour off-peak
        
        duration_hours = max(1, math.ceil(duration_min / 60))  # Minimum 1 hour
        return duration_hours * rate_per_hour
    
    def _estimate_toll_charges(self, distance_km: float) -> float:
        """Estimate toll charges."""
        # Bangalore has few toll roads within city
        # Only consider for longer distances
        if distance_km > 20:
            # Example: Mysore Road toll
            return 50  # INR
        return 0
    
    def calculate_time_value(self, duration_min: float, income_per_hour: float = 500) -> float:
        """
        Calculate the value of time spent traveling.
        
        Args:
            duration_min: Duration in minutes
            income_per_hour: Hourly income in INR (default 500)
            
        Returns:
            Value of time in INR
        """
        duration_hours = duration_min / 60
        return duration_hours * income_per_hour * 0.5  # 50% of income as value of leisure time
    
    def get_total_cost_of_ownership(self, mode: TransportMode, 
                                   monthly_distance_km: float = 500) -> Dict[str, float]:
        """
        Calculate total cost of ownership for different modes.
        
        Args:
            mode: Transportation mode
            monthly_distance_km: Average monthly distance
            
        Returns:
            Dictionary with cost breakdown
        """
        if mode == TransportMode.CAR:
            return self._get_car_ownership_cost(monthly_distance_km)
        elif mode == TransportMode.BIKE:
            return self._get_bike_ownership_cost(monthly_distance_km)
        else:
            # For public transport/walking, only operational costs
            monthly_cost = self.calculate_cost(mode, monthly_distance_km, 0)["total_cost"]
            return {
                "monthly_cost": monthly_cost,
                "annual_cost": monthly_cost * 12,
                "cost_per_km": monthly_cost / monthly_distance_km if monthly_distance_km > 0 else 0
            }
    
    def _get_car_ownership_cost(self, monthly_distance_km: float) -> Dict[str, float]:
        """Calculate car ownership costs."""
        # Assumptions for Bangalore
        car_price = 800000  # INR
        loan_interest_rate = 0.08  # 8% annually
        loan_years = 5
        insurance_per_year = 20000  # INR
        maintenance_per_year = 15000  # INR
        road_tax_per_year = 5000  # INR
        
        # Monthly loan EMI
        monthly_interest = loan_interest_rate / 12
        num_payments = loan_years * 12
        emi = (car_price * monthly_interest * (1 + monthly_interest) ** num_payments) / \
              ((1 + monthly_interest) ** num_payments - 1)
        
        # Monthly fixed costs
        monthly_fixed = (insurance_per_year + maintenance_per_year + road_tax_per_year) / 12
        
        # Monthly variable costs (fuel, etc.)
        monthly_variable = self.calculate_cost(TransportMode.CAR, monthly_distance_km, 0)["total_cost"]
        
        total_monthly = emi + monthly_fixed + monthly_variable
        
        return {
            "monthly_cost": total_monthly,
            "loan_emi": emi,
            "fixed_costs": monthly_fixed,
            "variable_costs": monthly_variable,
            "annual_cost": total_monthly * 12,
            "cost_per_km": total_monthly / monthly_distance_km if monthly_distance_km > 0 else 0
        }
    
    def _get_bike_ownership_cost(self, monthly_distance_km: float) -> Dict[str, float]:
        """Calculate bike ownership costs."""
        bike_price = 20000  # INR
        maintenance_per_year = 3000  # INR
        insurance_per_year = 1000  # INR
        
        # Assuming no loan for bike
        monthly_depreciation = bike_price / (5 * 12)  # 5 year lifespan
        monthly_fixed = (maintenance_per_year + insurance_per_year) / 12
        
        # Variable costs
        monthly_variable = self.calculate_cost(TransportMode.BIKE, monthly_distance_km, 0)["total_cost"]
        
        total_monthly = monthly_depreciation + monthly_fixed + monthly_variable
        
        return {
            "monthly_cost": total_monthly,
            "depreciation": monthly_depreciation,
            "fixed_costs": monthly_fixed,
            "variable_costs": monthly_variable,
            "annual_cost": total_monthly * 12,
            "cost_per_km": total_monthly / monthly_distance_km if monthly_distance_km > 0 else 0
        }
    
    def compare_costs(self, distance_km: float, duration_min: float) -> Dict[str, Dict[str, float]]:
        """
        Compare costs across all transportation modes.
        
        Args:
            distance_km: Distance in kilometers
            duration_min: Duration in minutes
            
        Returns:
            Dictionary with costs for each mode
        """
        comparison = {}
        
        for mode in TransportMode:
            cost_data = self.calculate_cost(mode, distance_km, duration_min)
            comparison[mode.value] = {
                "total_cost": cost_data["total_cost"],
                "cost_per_km": cost_data["cost_per_km"],
                "method": cost_data["method"]
            }
        
        return comparison