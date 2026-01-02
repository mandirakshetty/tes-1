import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
import polyline as google_polyline
from api.route_service import RouteService, Route 
class MapRenderer:
    """
    Renders interactive maps with realistic routes for different transportation modes.
    Uses Folium for interactive maps and can display detailed transit segments.
    """
    
    def __init__(self, default_zoom=13):
        """Initialize the map renderer."""
        self.default_zoom = default_zoom
    
    def create_interactive_map(self, routes, origin=None, destination=None):
        """
        Create an interactive Folium map with all routes.
        
        Args:
            routes (dict): Dictionary of routes by mode
            origin (tuple): Optional (lat, lng) for origin
            destination (tuple): Optional (lat, lng) for destination
            
        Returns:
            folium.Map: Interactive map object
        """
        # Determine map center
        if routes:
            # Use first route's first coordinate as center
            first_route = next(iter(routes.values()))
            if first_route['path']:
                center = first_route['path'][0]
            else:
                center = [40.7128, -74.0060]  # Default to NYC
        else:
            center = [40.7128, -74.0060]
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=self.default_zoom,
            tiles='cartodbpositron'  # Clean, light tiles
        )
        
        # Add each route to the map
        for mode, route in routes.items():
            self._add_route_to_map(m, route)
        
        # Add origin and destination markers if provided
        if origin:
            folium.Marker(
                location=origin,
                popup="Origin",
                icon=folium.Icon(color='green', icon='home', prefix='fa')
            ).add_to(m)
        
        if destination:
            folium.Marker(
                location=destination,
                popup="Destination",
                icon=folium.Icon(color='red', icon='flag', prefix='fa')
            ).add_to(m)
        
        # Add layer control for toggling routes
        folium.LayerControl().add_to(m)
        
        return m
    
    def _add_route_to_map(self, map_obj, route):
        """
        Add a single route to the Folium map with realistic paths.
        
        Args:
            map_obj (folium.Map): The map to add the route to
            route (dict): Route information
        """
        if not route or 'path' not in route or not route['path']:
            return
        
        mode = route.get('mode', 'unknown')
        color = route.get('color', '#000000')
        path_coords = route['path']
        
        # For transit routes, draw detailed segments
        if mode == 'transit' and 'transit_segments' in route:
            self._add_transit_segments(map_obj, route['transit_segments'])
        else:
            # For non-transit routes, draw the main path
            folium.PolyLine(
                locations=path_coords,
                color=color,
                weight=6,
                opacity=0.8,
                popup=f"{mode.capitalize()} Route",
                tooltip=f"Click for {mode} details"
            ).add_to(map_obj)
        
        # Add mode-specific markers
        if len(path_coords) > 1:
            # Add start marker
            folium.CircleMarker(
                location=path_coords[0],
                radius=5,
                color=color,
                fill=True,
                popup=f"Start of {mode} route"
            ).add_to(map_obj)
            
            # Add end marker
            folium.CircleMarker(
                location=path_coords[-1],
                radius=5,
                color=color,
                fill=True,
                popup=f"End of {mode} route"
            ).add_to(map_obj)
    
    def _add_transit_segments(self, map_obj, transit_segments):
        """
        Add detailed transit segments to the map.
        This ensures bus and metro lines are drawn separately with realistic paths.
        
        Args:
            map_obj (folium.Map): The map to add segments to
            transit_segments (list): List of transit segment dictionaries
        """
        if not transit_segments:
            return
        
        # Group segments by mode for better visualization
        segments_by_mode = {}
        for segment in transit_segments:
            mode = segment.get('mode', 'transit')
            if mode not in segments_by_mode:
                segments_by_mode[mode] = []
            segments_by_mode[mode].append(segment)
        
        # Draw each mode with appropriate styling
        for mode, segments in segments_by_mode.items():
            for segment in segments:
                path_coords = segment.get('path', [])
                if not path_coords:
                    continue
                
                # Different styling for different transit modes
                if mode == 'subway':
                    weight = 8
                    dash_array = None
                    opacity = 0.9
                    popup_text = f"Metro: {segment.get('line_name', 'Line')}"
                elif mode == 'bus':
                    weight = 6
                    dash_array = '10, 10'
                    opacity = 0.7
                    popup_text = f"Bus: {segment.get('line_name', 'Line')}"
                elif mode == 'train':
                    weight = 7
                    dash_array = '5, 5'
                    opacity = 0.8
                    popup_text = f"Train: {segment.get('line_name', 'Line')}"
                else:
                    weight = 5
                    dash_array = None
                    opacity = 0.6
                    popup_text = "Transit Segment"
                
                # Add detailed popup information
                popup_html = f"""
                <div style='font-family: Arial;'>
                    <h4>{popup_text}</h4>
                    <p><b>Agency:</b> {segment.get('agency', 'Unknown')}</p>
                    <p><b>From:</b> {segment.get('departure_stop', 'Unknown')}</p>
                    <p><b>To:</b> {segment.get('arrival_stop', 'Unknown')}</p>
                    <p><b>Stops:</b> {segment.get('num_stops', 0)}</p>
                    <p><b>Distance:</b> {segment.get('distance', 0)/1000:.1f} km</p>
                    <p><b>Duration:</b> {segment.get('duration', 0)/60:.0f} min</p>
                </div>
                """
                
                folium.PolyLine(
                    locations=path_coords,
                    color=segment.get('color', '#000000'),
                    weight=weight,
                    opacity=opacity,
                    dash_array=dash_array,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{mode.capitalize()}: {segment.get('line_name', '')}"
                ).add_to(map_obj)
                
                # Add station markers for transit
                if path_coords:
                    # Departure station
                    folium.CircleMarker(
                        location=path_coords[0],
                        radius=4,
                        color=segment.get('color', '#000000'),
                        fill=True,
                        fill_color='white',
                        fill_opacity=1,
                        popup=f"Depart: {segment.get('departure_stop', 'Station')}"
                    ).add_to(map_obj)
                    
                    # Arrival station
                    folium.CircleMarker(
                        location=path_coords[-1],
                        radius=4,
                        color=segment.get('color', '#000000'),
                        fill=True,
                        fill_color='white',
                        fill_opacity=1,
                        popup=f"Arrive: {segment.get('arrival_stop', 'Station')}"
                    ).add_to(map_obj)
    
    def display_route_comparison(self, routes, origin_name, destination_name):
        """
        Display a complete route comparison in Streamlit.
        
        Args:
            routes (dict): Dictionary of routes by mode
            origin_name (str): Name of origin location
            destination_name (str): Name of destination location
        """
        st.subheader(f"🚗 Route Comparison: {origin_name} to {destination_name}")
        
        if not routes:
            st.warning("No routes found. Please check your locations.")
            return
        
        # Create two columns for map and route info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create and display interactive map
            map_obj = self.create_interactive_map(routes)
            folium_static(map_obj, width=700, height=500)
        
        with col2:
            # Display route statistics
            st.markdown("### 📊 Route Details")
            
            for mode, route in routes.items():
                with st.expander(f"{mode.upper()}: {route.get('summary', 'Route')}"):
                    # Calculate eco score
                    eco_score = RouteService.calculate_eco_score(route)
                    
                    # Display metrics
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric(
                            "Distance",
                            f"{route['distance']/1000:.1f} km",
                            delta=None
                        )
                    
                    with col_b:
                        st.metric(
                            "Duration",
                            f"{route['duration']/60:.0f} min",
                            delta=None
                        )
                    
                    # Eco score with color coding
                    st.metric(
                        "Eco Score",
                        f"{eco_score:.0f}/100",
                        delta="Very Eco" if eco_score > 80 else "Moderate" if eco_score > 50 else "Less Eco"
                    )
                    
                    # Display warnings if any
                    if route.get('warnings'):
                        st.warning(f"⚠️ Note: {route['warnings'][0]}")
        
        # Display transit details if available
        if 'transit' in routes and 'transit_segments' in routes['transit']:
            self._display_transit_details(routes['transit']['transit_segments'])
    
    def _display_transit_details(self, transit_segments):
        """
        Display detailed transit segment information.
        
        Args:
            transit_segments (list): List of transit segment dictionaries
        """
        st.markdown("### 🚆 Transit Details")
        
        for i, segment in enumerate(transit_segments, 1):
            mode_icon = {
                'subway': '🚇',
                'bus': '🚌',
                'train': '🚂',
                'transit': '🚊'
            }.get(segment.get('mode', 'transit'), '🚊')
            
            with st.expander(f"{mode_icon} Segment {i}: {segment.get('line_name', 'Unknown Line')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**From:** {segment.get('departure_stop', 'Unknown')}")
                    st.markdown(f"**To:** {segment.get('arrival_stop', 'Unknown')}")
                
                with col2:
                    st.markdown(f"**Agency:** {segment.get('agency', 'Unknown')}")
                    st.markdown(f"**Stops:** {segment.get('num_stops', 0)}")
                
                with col3:
                    st.markdown(f"**Distance:** {segment.get('distance', 0)/1000:.1f} km")
                    st.markdown(f"**Duration:** {segment.get('duration', 0)/60:.0f} min")
    
    def generate_static_map_url(self, routes, size="800x600"):
        """
        Generate a Google Static Maps URL with all routes.
        Useful for simple, non-interactive displays.
        
        Args:
            routes (dict): Dictionary of routes by mode
            size (str): Map dimensions
            
        Returns:
            str: Static map URL
        """
        # This requires the GoogleMapsClient to be passed or available
        # For simplicity, we'll return a placeholder
        # In practice, you'd integrate this with GoogleMapsClient.get_static_map_url()
        
        paths_for_map = []
        for mode, route in routes.items():
            if route and route.get('path'):
                paths_for_map.append({
                    'coords': route['path'],
                    'color': route.get('color', '#000000')
                })
        
        # Note: You'll need to pass a GoogleMapsClient instance to use this fully
        # return self.google_client.get_static_map_url(paths_for_map, size=size)
        
        return "Static map URL would be generated here with GoogleMapsClient"