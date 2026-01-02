"""
Emission calculator for different transportation modes.
"""

from typing import Dict, Tuple
import math
from dataclasses import dataclass
from enum import Enum

from config.settings import Settings
from utils.constants import TransportMode

class FuelType(str, Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    CNG = "cng"
    ELECTRIC = "electric"
    HYBRID = "hybrid"

@dataclass
class EmissionFactors:
    """Emission factors for different fuel types (kg CO2 per unit)."""
    # kg CO2 per liter
    petrol: float = 2.31
    diesel: float = 2.68
    cng: float = 2.75  # per kg
    # kg CO2 per kWh (Indian grid average)
    electricity: float = 0.82
    hybrid: float = 1.55  # Average of petrol and electric

class EmissionCalculator:
    """Calculator for CO2 emissions and environmental impact."""
    
    def __init__(self):
        self.factors = EmissionFactors()
        self.settings = Settings
    
    def calculate_co2_emissions(self, mode: TransportMode, distance_km: float,
                               vehicle_type: str = None) -> Dict[str, float]:
        """
        Calculate CO2 emissions for a trip.
        
        Args:
            mode: Transportation mode
            distance_km: Distance in kilometers
            vehicle_type: Optional vehicle type specification
            
        Returns:
            Dictionary with emissions data
        """
        if mode == TransportMode.CAR:
            return self._calculate_car_emissions(distance_km, vehicle_type)
        elif mode == TransportMode.METRO:
            return self._calculate_metro_emissions(distance_km)
        elif mode == TransportMode.BUS:
            return self._calculate_bus_emissions(distance_km)
        elif mode == TransportMode.BIKE:
            return self._calculate_bike_emissions(distance_km)
        elif mode == TransportMode.WALK:
            return self._calculate_walk_emissions(distance_km)
        else:
            # Default calculation using settings
            mode_config = self.settings.TRANSPORT_MODES[mode.value]
            emissions = distance_km * self._get_emission_factor(mode)
            return {
                "co2_kg": emissions,
                "co2_per_km": self._get_emission_factor(mode),
                "method": "default"
            }
    
    def _calculate_car_emissions(self, distance_km: float, vehicle_type: str = None) -> Dict[str, float]:
        """Calculate car emissions based on fuel type and efficiency."""
        # Default values for Bangalore
        if vehicle_type == "diesel":
            fuel_efficiency = 18  # km per liter
            co2_per_liter = self.factors.diesel
        elif vehicle_type == "cng":
            fuel_efficiency = 20  # km per kg
            co2_per_liter = self.factors.cng
        elif vehicle_type == "electric":
            energy_efficiency = 0.15  # kWh per km
            co2_per_kwh = self.factors.electricity
            emissions = distance_km * energy_efficiency * co2_per_kwh
            return {
                "co2_kg": emissions,
                "co2_per_km": energy_efficiency * co2_per_kwh,
                "energy_kwh": distance_km * energy_efficiency,
                "method": "electric"
            }
        elif vehicle_type == "hybrid":
            fuel_efficiency = 22  # km per liter
            co2_per_liter = self.factors.hybrid
        else:  # petrol (default)
            fuel_efficiency = 15  # km per liter
            co2_per_liter = self.factors.petrol
        
        fuel_consumed = distance_km / fuel_efficiency
        emissions = fuel_consumed * co2_per_liter
        
        return {
            "co2_kg": emissions,
            "co2_per_km": co2_per_liter / fuel_efficiency,
            "fuel_liters": fuel_consumed,
            "fuel_efficiency": fuel_efficiency,
            "method": vehicle_type or "petrol"
        }
    
    def _calculate_metro_emissions(self, distance_km: float) -> Dict[str, float]:
        """Calculate metro emissions (electric)."""
        # Metro energy consumption per passenger-km
        energy_per_km = 0.15  # kWh per passenger-km (Bangalore metro average)
        co2_per_kwh = self.factors.electricity
        
        energy_consumed = distance_km * energy_per_km
        emissions = energy_consumed * co2_per_kwh
        
        return {
            "co2_kg": emissions,
            "co2_per_km": energy_per_km * co2_per_kwh,
            "energy_kwh": energy_consumed,
            "method": "electric_metro"
        }
    
    def _calculate_bus_emissions(self, distance_km: float) -> Dict[str, float]:
        """Calculate bus emissions (diesel)."""
        # Bus fuel efficiency and occupancy
        fuel_efficiency = 4  # km per liter (diesel bus)
        average_occupancy = 40  # passengers
        co2_per_liter = self.factors.diesel
        
        # Emissions per passenger
        fuel_per_passenger_km = 1 / (fuel_efficiency * average_occupancy)
        emissions = distance_km * fuel_per_passenger_km * co2_per_liter
        
        return {
            "co2_kg": emissions,
            "co2_per_km": fuel_per_passenger_km * co2_per_liter,
            "fuel_per_passenger_liter": distance_km * fuel_per_passenger_km,
            "method": "diesel_bus"
        }
    
    def _calculate_bike_emissions(self, distance_km: float) -> Dict[str, float]:
        """Calculate bike emissions (human power = zero emissions)."""
        # For regular bike - zero emissions from transportation
        calories_per_km = 35  # calories burned per km cycling
        food_emissions_per_calorie = 0.001  # kg CO2 per calorie (very rough estimate)
        
        emissions = distance_km * calories_per_km * food_emissions_per_calorie
        
        return {
            "co2_kg": emissions,
            "co2_per_km": calories_per_km * food_emissions_per_calorie,
            "calories_burned": distance_km * calories_per_km,
            "method": "human_power"
        }
    
    def _calculate_walk_emissions(self, distance_km: float) -> Dict[str, float]:
        """Calculate walking emissions (human power)."""
        calories_per_km = 70  # calories burned per km walking
        food_emissions_per_calorie = 0.001  # kg CO2 per calorie
        
        emissions = distance_km * calories_per_km * food_emissions_per_calorie
        
        return {
            "co2_kg": emissions,
            "co2_per_km": calories_per_km * food_emissions_per_calorie,
            "calories_burned": distance_km * calories_per_km,
            "method": "human_power"
        }
    
    def _get_emission_factor(self, mode: TransportMode) -> float:
        """Get emission factor for a transportation mode."""
        if mode == TransportMode.CAR:
            return Settings.CAR_EMISSIONS_PER_KM
        elif mode == TransportMode.BUS:
            return Settings.BUS_EMISSIONS_PER_KM
        elif mode == TransportMode.METRO:
            return Settings.METRO_EMISSIONS_PER_KM
        elif mode == TransportMode.BIKE:
            return Settings.BIKE_EMISSIONS_PER_KM
        elif mode == TransportMode.WALK:
            return Settings.WALK_EMISSIONS_PER_KM
        else:
            return 0.0
    
    def calculate_equivalent_impact(self, co2_kg: float) -> Dict[str, str]:
        """
        Calculate equivalent environmental impact for educational purposes.
        
        Args:
            co2_kg: CO2 emissions in kilograms
            
        Returns:
            Dictionary with equivalent impacts
        """
        equivalents = {
            "tree_months": f"A tree absorbs this much CO2 in {co2_kg / 21:.1f} months",
            "smartphone_charges": f"Equivalent to {co2_kg * 1000:.0f} smartphone charges",
            "km_driven": f"Same as driving a car for {co2_kg * 8.33:.1f} km",
            "lightbulb_hours": f"Powering a LED bulb for {co2_kg * 12:.0f} hours",
            "water_bottles": f"Manufacturing {co2_kg * 20:.0f} plastic water bottles"
        }
        
        return equivalents
    
    def calculate_health_benefits(self, mode: TransportMode, distance_km: float) -> Dict[str, float]:
        """
        Calculate health benefits of active transportation.
        
        Args:
            mode: Transportation mode
            distance_km: Distance in kilometers
            
        Returns:
            Dictionary with health benefits
        """
        if mode == TransportMode.BIKE:
            calories = distance_km * 35  # calories per km cycling
            health_score = distance_km * 10  # arbitrary health score
        elif mode == TransportMode.WALK:
            calories = distance_km * 70  # calories per km walking
            health_score = distance_km * 15
        else:
            calories = 0
            health_score = 0
        
        return {
            "calories_burned": calories,
            "health_score": health_score,
            "cardiovascular_benefit": "High" if mode in [TransportMode.BIKE, TransportMode.WALK] else "Low",
            "air_pollution_exposure": "Low" if mode in [TransportMode.BIKE, TransportMode.WALK] else "High"
        }
    
    def get_emission_comparison(self, distance_km: float) -> Dict[str, Dict[str, float]]:
        """
        Compare emissions across all transportation modes.
        
        Args:
            distance_km: Distance in kilometers
            
        Returns:
            Dictionary with emissions for each mode
        """
        comparison = {}
        
        for mode in TransportMode:
            emissions_data = self.calculate_co2_emissions(mode, distance_km)
            comparison[mode.value] = {
                "co2_kg": emissions_data["co2_kg"],
                "co2_per_km": emissions_data["co2_per_km"],
                "method": emissions_data["method"]
            }
        
        return comparison