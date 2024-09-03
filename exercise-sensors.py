#!/usr/bin/env python3
""" Main tracker loop """

import time

import lib

import utils



def main():
    sensors = lib.Sensors()
    gps = lib.Gps()

    while True:
        gps_location = None
        gps_location = gps.read()
        if not gps_location:
            utils.print_status_char(".")
            time.sleep(2)
            continue
        bme280_data = sensors.get_bme280()
        packet_params = {
            'temperature': round(bme280_data.temperature, 1),
            'humidity': round(bme280_data.humidity, 1),
            'pressure': round(bme280_data.pressure, 1),
            'internal_temperature': round(sensors.get_lm75_temperature(), 1),
        }
        packet_params.update({
            'num_sats': int(gps_location.num_sats),
            'time': gps_location.timestamp.isoformat() if gps_location.timestamp else "00:00:00",
        })
        if gps_location.gps_qual == 0: # we have no GPS fix
            packet_params.update({
                'uptime': utils.uptime()
            })
        else:
            had_initial_fix = True
            packet_params.update({
                'alt': int(round(gps_location.altitude, 1)),
                'lat': round(gps_location.latitude, 6),
                'lon': round(gps_location.longitude, 6),
            })
        time.sleep(2)


if __name__ == "__main__":
    main()
