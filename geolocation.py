"""
Módulo de geolocalización y cálculo de distancias.
"""

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Optional, Tuple, Dict
import time


class GeoLocator:
    """Clase para manejar geocodificación y cálculo de distancias."""
    
    def __init__(self):
        """Inicializa el geocodificador."""
        self.geolocator = Nominatim(user_agent="news_monitor_monterrey")
        
        # Coordenadas aproximadas para ubicaciones genéricas
        self.generic_coords = {
            'monterrey': (25.6866, -100.3161),  # Centro de Monterrey
            'centro': (25.6692, -100.3099),
            'san pedro': (25.6520, -100.4092),
            'san pedro garza garcía': (25.6520, -100.4092),
            'garza garcía': (25.6520, -100.4092),
            'guadalupe': (25.6767, -100.2561),
            'san nicolás': (25.7420, -100.2990),
            'escobedo': (25.7959, -100.3185),
            'apodaca': (25.7803, -100.1867),
            'santa catarina': (25.6747, -100.4597),
            'garcía': (25.8075, -100.5892),
            'pesquería': (25.7833, -99.9833),
            'cumbres': (25.7295, -100.3928),  # Área Cumbres
            'valle oriente': (25.6397, -100.3176),  # Valle Oriente
            'carretera nacional': (25.5781, -100.2512),  # Zona Carretera Nacional
        }
    
    def geocode_location(self, location_text: str) -> Optional[Tuple[float, float]]:
        """
        Convierte una dirección de texto en coordenadas geográficas.
        
        Args:
            location_text: Texto con la ubicación (ej. "Av. Gonzalitos, Monterrey")
        
        Returns:
            Tupla (latitud, longitud) o None si no se puede geocodificar
        """
        try:
            location_lower = location_text.lower().strip()
            
            # Primero, verificar si es una ubicación genérica conocida
            for area, coords in self.generic_coords.items():
                if area in location_lower:
                    print(f"  ✓ Usando coordenadas aproximadas para '{area}'")
                    return coords
            
            # Si no es genérica, intentar geocodificación precisa
            # Agregar "Monterrey, Nuevo León, México" para mejorar precisión
            full_location = f"{location_text}, Monterrey, Nuevo León, México"
            
            # Realizar geocodificación
            location = self.geolocator.geocode(full_location, timeout=10)
            
            if location:
                return (location.latitude, location.longitude)
            else:
                # Intentar sin el contexto adicional
                location = self.geolocator.geocode(location_text, timeout=10)
                if location:
                    return (location.latitude, location.longitude)
            
            return None
        
        except Exception as e:
            print(f"Error en geocodificación: {e}")
            return None
    
    def calculate_distance(self, coord1: Tuple[float, float], 
                          coord2: Tuple[float, float]) -> float:
        """
        Calcula la distancia en kilómetros entre dos coordenadas.
        
        Args:
            coord1: Tupla (latitud, longitud) del primer punto
            coord2: Tupla (latitud, longitud) del segundo punto
        
        Returns:
            Distancia en kilómetros
        """
        try:
            return geodesic(coord1, coord2).kilometers
        except Exception as e:
            print(f"Error calculando distancia: {e}")
            return float('inf')
    
    def find_nearest_costco(self, event_coords: Tuple[float, float],
                           costco_locations: Dict) -> Optional[Dict]:
        """
        Encuentra la sucursal de Costco más cercana a un evento.
        
        Args:
            event_coords: Coordenadas del evento (lat, lon)
            costco_locations: Diccionario con las ubicaciones de Costco
        
        Returns:
            Diccionario con información de la sucursal más cercana y distancia
        """
        nearest = None
        min_distance = float('inf')
        
        for name, info in costco_locations.items():
            costco_coords = (info['lat'], info['lon'])
            distance = self.calculate_distance(event_coords, costco_coords)
            
            if distance < min_distance:
                min_distance = distance
                nearest = {
                    'nombre': name,
                    'distancia_km': round(distance, 2),
                    'direccion': info['direccion']
                }
        
        return nearest
    
    def is_within_radius(self, event_coords: Tuple[float, float],
                        costco_locations: Dict, radius_km: float) -> Tuple[bool, Optional[Dict]]:
        """
        Verifica si un evento está dentro del radio de alguna sucursal de Costco.
        
        Args:
            event_coords: Coordenadas del evento
            costco_locations: Diccionario con ubicaciones de Costco
            radius_km: Radio en kilómetros
        
        Returns:
            Tupla (está_dentro_del_radio, info_sucursal_mas_cercana)
        """
        nearest = self.find_nearest_costco(event_coords, costco_locations)
        
        if nearest and nearest['distancia_km'] <= radius_km:
            return (True, nearest)
        
        return (False, nearest)

