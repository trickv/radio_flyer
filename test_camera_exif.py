#!/usr/bin/env python

from camera import Camera
import subprocess
import datetime

cam = Camera()

lat = 41.899839
lon = -84.048052

data = {
    'seq': 42,
    'temperature': 22.1,
    'pressure': 1022.9,
    'humidity': 42.65,
#    'lat': 42.12345,
#    'lon': -1.928,
    'lat': lat,
    'lon': lon,
    #'latref': 'S' if lat < 0 else 'N',
    #'lonref': 'E' if lon > 0 else 'W',
    'alt': 123.5,
    'num_sats': 88,
    'time': datetime.datetime.now().time().strftime("%H:%M:%S"),
}




f = cam.take_photo(data, delay=0)

subprocess.call(["exiftool", "-g", f])
print(data)
