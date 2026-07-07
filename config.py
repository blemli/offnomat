#!/usr/bin/env python3
import json
from icecream import ic

items = []

# default: turn the LEDs off when the light sensor reports darkness.
# can be disabled per-device in admin/static/config.json ("night_mode": false)
night_mode = True

try:
    with open('admin/static/config.json') as file:
        config = json.load(file)
        mode=config["mode"]
        items.append(mode)
        places=config["places"]
        items.append(places)
        graphhopper_key=config.get("graphhopper_key")
        items.append(graphhopper_key)
        night_mode=config.get("night_mode", True)
        items.append(night_mode)

except FileNotFoundError:
    logging.error("config.json not found, please go to offnomat.local to edit config")


def dump():
    ic(items)


if __name__ == "__main__":
    dump()
