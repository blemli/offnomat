#!/usr/bin/env python3

import sys
import os
import json
import logging
from datetime import datetime, timedelta

import requests
from geopy.geocoders import Nominatim

from config import graphhopper_key
# reuse hours.py's resilient Overpass client (https + User-Agent + retry + mirror)
from hours import find_place, overpass_get

VEHICLES = ["foot", "bike", "car"]
CACHE_FILE = "travel_times_cache.json"
CACHE_DURATION_DAYS = 10

# Center coordinates for Winterthur (the offnomat's home location)
WINTERTHUR_LAT = 47.49973
WINTERTHUR_LON = 8.72413


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
            cache_date = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_date < timedelta(days=CACHE_DURATION_DAYS):
                return cache['data']
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return {}


def save_cache(cache_data):
    cache = {'timestamp': datetime.now().isoformat(), 'data': cache_data}
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def get_cache_key(source, destination, means):
    return f"{source}|{destination}|{means}"


def geocode(address):
    """Return (lat, lon) for a place name, or None if it can't be located."""
    osm_id = find_place(WINTERTHUR_LAT, WINTERTHUR_LON, address)
    if osm_id:
        query = f"""
        [out:json];
        (node({osm_id}); way({osm_id}); relation({osm_id}););
        out center;
        """
        response = overpass_get(query)
        if response is not None:
            elements = response.json().get('elements', [])
            if elements:
                element = elements[0]
                lat = element.get('center', {}).get('lat', element.get('lat'))
                lon = element.get('center', {}).get('lon', element.get('lon'))
                if lat is not None and lon is not None:
                    return lat, lon
    # Fallback to Nominatim if the OSM lookup fails
    try:
        geolocator = Nominatim(user_agent="offnomat")
        location = geolocator.geocode(f"{address}, Winterthur, Switzerland")
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        logging.warning(f"geocode fallback failed for {address}: {e}")
    return None


def _route_minutes(src_lat, src_lng, dst_lat, dst_lng, means):
    """Query GraphHopper for travel time in minutes, or None on any failure."""
    if not graphhopper_key:
        return None
    url = (f"https://graphhopper.com/api/1/route?point={src_lat},{src_lng}"
           f"&point={dst_lat},{dst_lng}&vehicle={means}&key={graphhopper_key}")
    try:
        data = requests.get(url, timeout=30).json()
    except requests.RequestException as e:
        logging.warning(f"graphhopper request failed: {e}")
        return None
    paths = data.get("paths")
    if not paths:
        logging.warning(f"graphhopper: no route ({data.get('message', '')})")
        return None
    return round(paths[0]["time"] / 60000)


def travel_minutes(source, destination, means):
    """Travel minutes between two place names, cached for CACHE_DURATION_DAYS."""
    cache = load_cache()
    cache_key = get_cache_key(source, destination, means)
    if cache_key in cache:
        return cache[cache_key]

    src = geocode(source)
    dst = geocode(destination)
    if src is None or dst is None:
        return None

    minutes = _route_minutes(src[0], src[1], dst[0], dst[1], means)
    if minutes is not None:
        cache[cache_key] = minutes
        save_cache(cache)
    return minutes


def travel_from_center(destination, means):
    """Travel minutes from the offnomat's home location to a place name.

    Returns int minutes, or None if unavailable (no API key, geocode failure,
    or routing failure). Cached for CACHE_DURATION_DAYS.
    """
    cache = load_cache()
    cache_key = get_cache_key("__center__", destination, means)
    if cache_key in cache:
        return cache[cache_key]
    if not graphhopper_key:
        return None

    dst = geocode(destination)
    if dst is None:
        return None

    minutes = _route_minutes(WINTERTHUR_LAT, WINTERTHUR_LON, dst[0], dst[1], means)
    if minutes is not None:
        cache[cache_key] = minutes
        save_cache(cache)
    return minutes


def test_all_locations():
    with open('admin/static/config.json', 'r') as f:
        config = json.load(f)
    places = [place['name'] for place in config['places'] if place['name']]
    print(f"Testing travel time from center to {len(places)} locations...")
    for name in places:
        for means in VEHICLES:
            print(f"  {name} [{means}]: {travel_from_center(name, means)} min")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        test_all_locations()
    elif len(sys.argv) == 4:
        source, destination, means = sys.argv[1], sys.argv[2], sys.argv[3]
        if means not in VEHICLES:
            print("Invalid means. Choose from foot, bike, car")
            sys.exit(1)
        print(travel_minutes(source, destination, means))
    else:
        print("Usage: travel_minutes.py [source destination means]")
        print("  no args: travel time from center to all config places")
        sys.exit(1)
