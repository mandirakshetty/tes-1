"""
Constants for the EcoRoute application.
"""

from enum import Enum

class RoutePriority(str, Enum):
    ECO_FRIENDLY = "Most Eco-Friendly"
    FASTEST = "Fastest"
    CHEAPEST = "Cheapest"
    BALANCED = "Balanced"
    COMFORT = "Most Comfortable"

class TransportMode(str, Enum):
    CAR = "car"
    METRO = "metro"
    BUS = "bus"
    BIKE = "bike"
    WALK = "walk"

class EcoScoreCategory(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very Poor"

# Thresholds for eco-score categories
ECO_SCORE_THRESHOLDS = {
    EcoScoreCategory.EXCELLENT: 80,
    EcoScoreCategory.GOOD: 60,
    EcoScoreCategory.MODERATE: 40,
    EcoScoreCategory.POOR: 20,
    EcoScoreCategory.VERY_POOR: 0
}

# Color scheme for eco-score categories
ECO_SCORE_COLORS = {
    EcoScoreCategory.EXCELLENT: "#2E7D32",  # Dark Green
    EcoScoreCategory.GOOD: "#43A047",       # Green
    EcoScoreCategory.MODERATE: "#FB8C00",   # Orange
    EcoScoreCategory.POOR: "#E53935",       # Red
    EcoScoreCategory.VERY_POOR: "#B71C1C"   # Dark Red
}

# Map icon configurations
MAP_ICONS = {
    "start": {"color": "green", "icon": "play", "prefix": "fa"},
    "end": {"color": "red", "icon": "stop", "prefix": "fa"},
    "metro": {"color": "purple", "icon": "subway", "prefix": "fa"},
    "bus": {"color": "orange", "icon": "bus", "prefix": "fa"},
    "transfer": {"color": "blue", "icon": "exchange", "prefix": "fa"},
    "walk": {"color": "gray", "icon": "walking", "prefix": "fa"}
}

# Time conversion constants
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60
METERS_PER_KM = 1000

# Cost constants (INR)
FUEL_COST_PER_LITER = 100  # Approx petrol price
AVERAGE_FUEL_EFFICIENCY = 15  # km per liter for car
METRO_BASE_FARE = 10
METRO_PER_KM_FARE = 2.5
BUS_BASE_FARE = 5
BUS_PER_KM_FARE = 1.0

# Environmental constants
CO2_PER_LITER_PETROL = 2.31  # kg CO2 per liter
CO2_PER_KWH_ELECTRICITY = 0.82  # kg CO2 per kWh (Indian grid average)
METRO_ENERGY_PER_KM = 0.15  # kWh per km per passenger
BUS_FUEL_EFFICIENCY = 4  # km per liter (diesel)

# Weather impact factors
WEATHER_IMPACT = {
    "clear": 1.0,
    "cloudy": 1.0,
    "rain": 0.8,  # 20% slower in rain
    "heavy_rain": 0.6,  # 40% slower
    "fog": 0.9  # 10% slower
}

# Traffic impact factors (for Bangalore)
TRAFFIC_IMPACT = {
    "off_peak": 1.0,
    "moderate": 0.8,  # 20% slower
    "heavy": 0.6,  # 40% slower
    "severe": 0.4  # 60% slower
}

# Time windows for traffic
TRAFFIC_WINDOWS = {
    "morning_peak": ("07:00", "10:00"),
    "evening_peak": ("17:00", "20:00"),
    "off_peak": None
}

# Accessibility factors
ACCESSIBILITY_FACTORS = {
    "car": {"parking": 0.9, "access": 1.0},
    "metro": {"parking": 1.0, "access": 0.8},  # Walking to station
    "bus": {"parking": 1.0, "access": 0.9},
    "bike": {"parking": 0.7, "access": 1.0},
    "walk": {"parking": 1.0, "access": 1.0}
}

# Carbon offset equivalents (for educational purposes)
CARBON_OFFSET_EQUIVALENTS = {
    "tree_months": 21,  # kg CO2 absorbed by a tree in 3 months
    "smartphone_charges": 1000,  # smartphone charges per kg CO2
    "km_driven": 8.33  # km driven by average car per kg CO2
}