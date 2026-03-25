#!/usr/bin/env python3

import sys
import requests
import json
from datetime import datetime, timedelta
from config import graphhopper_key
from icecream import ic
import os
from geopy.geocoders import Nominatim

means=["foot","bike","car"]
CACHE_FILE = "travel_times_cache.json"
CACHE_DURATION_DAYS = 10

# Center coordinates for Winterthur
WINTERTHUR_LAT = 47.49973
WINTERTHUR_LON = 8.72413

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            # Check if cache is expired
            cache_date = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_date < timedelta(days=CACHE_DURATION_DAYS):
                return cache['data']
    return {}

def save_cache(cache_data):
    cache = {
        'timestamp': datetime.now().isoformat(),
        'data': cache_data
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_cache_key(source, destination, means):
    return f"{source}|{destination}|{means}"

def find_place(lat, lon, search_name, radius=10000):
    """
    Find the nearest OSM ID by name from a given latitude and longitude.
    
    Parameters:
    - lat, lon: Latitude and longitude of the anchor point.
    - search_name: The name of the entity you're looking for, case-insensitive.
    - radius: Search radius in meters.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
      node["alt_name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
      way["name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
      way["alt_name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
      relation["name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
      relation["alt_name"~"{search_name}", i]({lat - 0.09},{lon - 0.09},{lat + 0.09},{lon + 0.09});
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    nearest_entity = None
    shortest_distance = float('inf')

    for element in data['elements']:
        # Calculate distance from anchor to element center (simplified calculation)
        elat = element.get('center', {}).get('lat', element.get('lat'))
        elon = element.get('center', {}).get('lon', element.get('lon'))
        distance = ((lat - elat) ** 2 + (lon - elon) ** 2) ** 0.5  # Simplified, not geographically accurate method

        if distance < shortest_distance:
            nearest_entity = element
            shortest_distance = distance

    if nearest_entity:
        return nearest_entity['id']  # Optionally return more info here
    else:
        return None

def geocode(address):
    # First try to find the place in OSM
    osm_id = find_place(WINTERTHUR_LAT, WINTERTHUR_LON, address)
    if osm_id:
        # Get coordinates from Overpass API
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        (
          node({osm_id});
          way({osm_id});
          relation({osm_id});
        );
        out center;
        """
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        
        if data['elements']:
            element = data['elements'][0]
            lat = element.get('center', {}).get('lat', element.get('lat'))
            lon = element.get('center', {}).get('lon', element.get('lon'))
            return lat, lon
    
    # Fallback to Nominatim if OSM lookup fails
    geolocator = Nominatim(user_agent="offnomat")
    location = geolocator.geocode(f"{address}, Winterthur, Switzerland")
    return location.latitude, location.longitude

def travel_minutes(source, destination, means):
    cache = load_cache()
    cache_key = get_cache_key(source, destination, means)
    
    if cache_key in cache:
        return cache[cache_key]
    
    source_lat, source_lng = geocode(source)
    dest_lat, dest_lng = geocode(destination)
    
    url = f"https://graphhopper.com/api/1/route?point={source_lat},{source_lng}&point={dest_lat},{dest_lng}&vehicle={means}&key={graphhopper_key}"
    response = requests.get(url)
    data = response.json()
    
    if "paths" not in data or not data["paths"]:
        return None
    
    # Convert milliseconds to minutes
    travel_time_ms = data["paths"][0]["time"]
    travel_time_minutes = round(travel_time_ms / 60000)
    
    # Save to cache
    cache[cache_key] = travel_time_minutes
    save_cache(cache)
    
    return travel_time_minutes

def test_all_locations():
    with open('admin/static/config.json', 'r') as f:
        config = json.load(f)
    
    places = [place['name'] for place in config['places'] if place['name']]
    print(f"Testing {len(places)} locations...")
    
    for i, source in enumerate(places):
        for j, destination in enumerate(places):
            if i != j:  # Skip same location
                print(f"\n{source} -> {destination}:")
                for means in ["bike", "foot", "car"]:
                    time = travel_minutes(source, destination, means)
                    print(f"{means}: {time} minutes")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        test_all_locations()
    elif len(sys.argv) == 4:
        if sys.argv[3] not in means:
            print("Invalid means. Choose from foot, bike, car")
            sys.exit(1)
        source = sys.argv[1]
        destination = sys.argv[2]
        means = sys.argv[3]
        print(geocode(source))
        print(geocode(destination))
        result = travel_minutes(source, destination, means)
        print(result)
    else:
        print("Usage: travel_minutes.py [source destination means]")
        print("Without arguments, tests all locations from config.json")
        sys.exit(1)
