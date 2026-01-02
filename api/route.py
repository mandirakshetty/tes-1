# api/route.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from utils.constants import TransportMode

@dataclass
class Route:
    """Data class representing a complete route."""
    
    # Route identification
    mode: TransportMode
    start_address: str
    end_address: str
    start_location: Tuple[float, float]  # (lat, lng)
    end_location: Tuple[float, float]    # (lat, lng)
    
    # Route metrics
    total_distance_km: float
    total_duration_min: float
    cost_inr: float
    co2_emissions_kg: float
    eco_score: float
    
    # Route details
    polyline: Optional[str] = None
    decoded_path: List[Tuple[float, float]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    transit_details: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    
    # Additional metadata
    calculation_time: datetime = field(default_factory=datetime.now)
    is_realistic: bool = False
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure decoded_path is populated if polyline exists
        if self.polyline and not self.decoded_path:
            try:
                import googlemaps
                decoded = googlemaps.convert.decode_polyline(self.polyline)
                self.decoded_path = [(p["lat"], p["lng"]) for p in decoded]
            except:
                # Fallback to simple path if decoding fails
                self.decoded_path = [self.start_location, self.end_location]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert route to dictionary for serialization."""
        return {
            'mode': self.mode.value,
            'start_address': self.start_address,
            'end_address': self.end_address,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'distance_km': self.total_distance_km,
            'duration_min': self.total_duration_min,
            'cost_inr': self.cost_inr,
            'co2_kg': self.co2_emissions_kg,
            'eco_score': self.eco_score,
            'steps': self.steps,
            'warnings': self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Route':
        """Create Route instance from dictionary."""
        from utils.constants import TransportMode
        
        return cls(
            mode=TransportMode(data['mode']),
            start_address=data['start_address'],
            end_address=data['end_address'],
            start_location=tuple(data['start_location']),
            end_location=tuple(data['end_location']),
            total_distance_km=data['distance_km'],
            total_duration_min=data['duration_min'],
            cost_inr=data['cost_inr'],
            co2_emissions_kg=data['co2_kg'],
            eco_score=data['eco_score'],
            steps=data.get('steps', []),
            warnings=data.get('warnings', [])
        )