import atexit
import logging
from datetime import datetime

import hours,colors,time
import led
import atexit

from led import pixels
from icecream import ic
from config import places, night_mode, mode
from light import is_dark
from travel_minutes import travel_from_center

LED_COUNT = 16
places=places[:LED_COUNT]

lat=47.49973
lon=8.72413

# config.mode -> GraphHopper vehicle; only foot/bike/car are supported
_MODE_ALIASES = {"pedestrian": "foot", "walk": "foot", "bicycle": "bike"}
vehicle = _MODE_ALIASES.get(mode, mode)
if vehicle not in ("foot", "bike", "car"):
    vehicle = "bike"

atexit.register(led.cleanup)
while True:
    if night_mode and is_dark():
        led.cleanup()
        logging.info("Disabeling because of Night")
    else:
        for i,place in enumerate(places):
            duration=place["duration"]
            place=place["name"]
            oh=hours.get(place,lat,lon)
            if place == "Diethelm":
                pixels[i]=colors.WHITE.rgb
                continue
            if oh is None:
                logging.error(f"{place} doesn't exist or has no hours")
                pixels[i]=colors.BLACK.rgb
                continue
            now = datetime.now()
            next_change = oh.next_change()
            if not oh.is_open():
                # closed: blue if it opens again very soon, else red
                minutes = (next_change - now).total_seconds() / 60 if next_change else None
                if minutes is not None and 0 < minutes < 15:
                    print(f"{place} opens soon (in {minutes:.0f} min)")
                    pixels[i]=colors.BLUE.rgb
                else:
                    print(f"{place} is closed")
                    pixels[i]=colors.RED.rgb
            elif next_change is None:
                # open with no scheduled close -> always time to go
                print(f"{place} is open (no scheduled close)")
                pixels[i]=colors.GREEN.rgb
            else:
                # open: can I travel there and still spend my time before it closes?
                minutes = (next_change - now).total_seconds() / 60
                travel = travel_from_center(place, vehicle)
                slack = minutes - duration - (travel or 0)
                tstr = f"{travel} min" if travel is not None else "n/a"
                if slack <= 0:
                    print(f"{place}: open but too late (closes in {minutes:.0f}, travel {tstr}, stay {duration})")
                    pixels[i]=colors.RED.rgb
                elif slack < 20:
                    print(f"{place}: only just (slack {slack:.0f} min, travel {tstr})")
                    pixels[i]=colors.PURPLE.rgb
                elif slack < 45:
                    print(f"{place}: doable (slack {slack:.0f} min, travel {tstr})")
                    pixels[i]=colors.ORANGE.rgb
                else:
                    print(f"{place}: open (slack {slack:.0f} min, travel {tstr})")
                    pixels[i]=colors.GREEN.rgb
    time.sleep(20)
