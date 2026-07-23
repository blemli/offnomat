#!/usr/bin/env python3
import json
import logging
from icecream import ic

items = []

# defaults, so importing these names never fails if config.json is missing or
# incomplete. night_mode: turn the LEDs off when the light sensor reports
# darkness (disable per-device with "night_mode": false).
mode = "bike"
places = []
graphhopper_key = None
night_mode = True

try:
    with open('admin/static/config.json') as file:
        config = json.load(file)
        mode=config.get("mode", mode)
        items.append(mode)
        places=config.get("places", places)
        items.append(places)
        graphhopper_key=config.get("graphhopper_key")
        items.append(graphhopper_key)
        night_mode=config.get("night_mode", True)
        items.append(night_mode)

except FileNotFoundError:
    logging.error("config.json not found, please go to offnomat.local to edit config")
except json.JSONDecodeError as e:
    logging.error(f"config.json is invalid JSON: {e}")


def dump():
    ic(items)


if __name__ == "__main__":
    dump()
