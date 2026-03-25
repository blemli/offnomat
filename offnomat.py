import atexit
import logging
from datetime import datetime

import hours,colors,time
import led
import atexit

from led import pixels
from icecream import ic
from config import places
from light import is_dark

LED_COUNT = 16
places=places[:LED_COUNT]

lat=47.49973
lon=8.72413

atexit.register(led.cleanup)
while True:
    if is_dark():
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
            # calculate minutes from now until next change (closing)
            if oh.next_change() is None:
                next_change=datetime.now()
            else:
                next_change=oh.next_change()
            minutes = (next_change - datetime.now()).seconds / 60
            if not oh.is_open():
                if minutes >0 and minutes < 15:
                    print(f"{place} opens soon (in {minutes} min")
                    pixels[i]=colors.BLUE.rgb
                else:
                    print(f"{place} is closed")
                    pixels[i]=colors.RED.rgb
            else:
                if minutes >0 and minutes < 20:
                    print(f"{place} closes very soon (in {minutes} min")
                    pixels[i]=colors.PURPLE.rgb
                elif minutes >= 20 and minutes < 45:
                    print(f"{place} closes soon")
                    pixels[i]=colors.ORANGE.rgb
                else:
                    print(f"{place} is open")
                    pixels[i]=colors.GREEN.rgb
    time.sleep(20)
