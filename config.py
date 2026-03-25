#!/usr/bin/env python3
import json
from icecream import ic

items = []

try:
    with open('admin/static/config.json') as file:
        config = json.load(file)
        mode=config["mode"]
        items.append(mode)
        places=config["places"]
        items.append(places)
        graphhopper_key=config.get("graphhopper_key")
        items.append(graphhopper_key)

except FileNotFoundError:
    logging.error("config.json not found, please go to offnomat.local to edit config")


def dump():
    ic(items)


if __name__ == "__main__":
    dump()
