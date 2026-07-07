import logging
import sys
import requests
from icecream import ic
from opening_hours import OpeningHours
import oh2
from geopy.geocoders import Nominatim
import urllib.parse

import requests_cache

requests_cache.install_cache('hours_cache', backend='sqlite', expire_after=3600)

# overpass-api.de blocks bare python-requests over plain HTTP (returns 406) and
# the http endpoint is flaky (504). Use HTTPS with a descriptive User-Agent.
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "offnomat/1.0 (https://problem.li; raspberry-pi opening-hours display)"}

def find_place(lat, lon, search_name, radius=10000):
    # Properly format search_name for regex matching in Overpass QL
    #search_name = search_name.replace(" ", ".*")  # Use '.*' to match any character including spaces between words
    """
    Find the nearest OSM ID by name from a given latitude and longitude.

    Parameters:
    - lat, lon: Latitude and longitude of the anchor point.
    - search_name: The name of the entity you're looking for, case-insensitive.
    - radius: Search radius in meters.
    """
    overpass_url = OVERPASS_URL
    #search_name = search_name.replace(" ", ".*")  # Use '.*' to match any character including spaces between words
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
    #print(overpass_query)
    response = requests.get(overpass_url, params={'data': overpass_query}, headers=HEADERS)
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


def get_hours_string(osm_id):
    # List of OSM types to iterate through
    osm_types = ["node", "way", "relation"]
    # Overpass API URL
    overpass_url = OVERPASS_URL

    for osm_type in osm_types:
        # Overpass QL (Query Language) to get opening hours
        overpass_query = f"""
        [out:json];
        ({osm_type}({osm_id});
        );
        out body;
        >;
        out skel qt;
        """
        # Attempt to fetch data for current osm_type
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=HEADERS)
        data = response.json()

        # Extracting opening hours from the response
        for element in data.get('elements', []):
            if 'tags' in element and 'opening_hours' in element['tags']:
                opening_hours = element['tags']['opening_hours']
                return opening_hours
    return None

import subprocess
import json
from datetime import datetime

def check_opening_hours(opening_hours_str, timestamp=datetime.now()):
    # Convert datetime to timestamp if necessary
    if isinstance(timestamp, datetime):
        timestamp = int(timestamp.timestamp() * 1000)  # Convert to milliseconds

    # Prepare the command
    cmd = ['node', 'opening_hours_check.js', opening_hours_str, str(timestamp)]

    # Execute the JavaScript script
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse JSON output
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise Exception(f"Error calling opening_hours_check.js: {result.stderr}")



def get(name, lat, lon):
    try:
        place=find_place(lat, lon, name)
        assert place is not None
    except:
        logging.error(f"Could not find {name}")
        return None
    try:
        hours_string=get_hours_string(place)
        ic(hours_string)
        oh=OpeningHours(hours_string)
        return oh
    except:
        logging.error(f"Could not get hours for {name}")
        return None

def get_by_id(id,lat,long):
    hours_string = get_hours_string(id)
    oh=check_opening_hours(hours_string)
#    oh = OpeningHours(hours_string)
    return oh


if __name__ =="__main__":
    lat = 47.49973
    lon = 8.72413
    if len(sys.argv) >1:
        name=sys.argv[1]
    else: name="Schwimmbad Geiselweid"
    oh=get(name, lat, lon)
    ic(oh.state())
    ic(oh.next_change())
    ic("end")
