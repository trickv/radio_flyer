#!/usr/bin/env python3
""" Main tracker loop """

import time

import crcmod
import lib

import utils

CALLSIGN = "EAGLE"

PACKET_TEMPLATES = {
    'operational': "{callsign},{seq},{time},{lat},{lon},{alt}," +
                   "{num_sats},{temperature},{pressure},{humidity}," +
                   "{internal_temperature},{voltage},{current}",
    'no_fix': "{callsign},{seq},NOFIX,{time},0,0,0,{num_sats}," +
              "{temperature},{pressure},{humidity},{uptime}," +
              "{internal_temperature},{voltage},{current}",
}
# try: http://habitat.habhub.org/genpayload/
#      payload -> create new
#      new format wizard
SENTENCE_TEMPLATE = "$${0}*{1:04X}\n"


def main():
    """ Main tracker loop. Never exits. """
    sequence = 0
    had_initial_fix = False
    transmitter = lib.Transmitter()
    transmitter.send("HAB tracker callsign {} starting up.\n".format(CALLSIGN), block=False)
    transmitter.send("Worlds best tracker software.\n", block=False)
    transmitter.send("Thanks to my lovely wife Sarah.\n", block=False)
    gps = lib.Gps()
    sensors = lib.Sensors()
    crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    transmitter.send("Tracker up and running. Lets fly!\n\n", block=False)

    while True:
        gps_location = None
        gps_location = gps.read()
        if not gps_location:
            utils.print_status_char(".")
            time.sleep(2)
            continue
        bme280_data = sensors.get_bme280()
        ina219_data = sensors.get_ina219()
        packet_params = {
            'callsign': CALLSIGN,
            'seq': sequence,
            'temperature': round(bme280_data.temperature, 1),
            'humidity': round(bme280_data.humidity, 1),
            'pressure': round(bme280_data.pressure, 1),
            'internal_temperature': round(sensors.get_lm75_temperature(), 1),
            'voltage': round(ina219_data[0], 2),
            'current': int(ina219_data[1]),
        }
        packet_params.update({
            'num_sats': int(gps_location.num_sats),
            'time': gps_location.timestamp.isoformat() if gps_location.timestamp else "00:00:00",
        })
        if gps_location.gps_qual == 0: # we have no GPS fix
            packet_template = PACKET_TEMPLATES['no_fix']
            packet_params.update({
                'uptime': utils.uptime()
            })
        else:
            had_initial_fix = True
            packet_template = PACKET_TEMPLATES['operational']
            packet_params.update({
                'alt': int(round(gps_location.altitude, 1)),
                'lat': round(gps_location.latitude, 6),
                'lon': round(gps_location.longitude, 6),
            })
        packet = packet_template.format(**packet_params)
        checksum = crc16f(packet.encode('ascii'))
        sentence = SENTENCE_TEMPLATE.format(packet, checksum)
        if not had_initial_fix:
            transmitter.send("{}: do not launch yet\n".format(CALLSIGN))
        transmitter.send(sentence)
        sequence += 1


if __name__ == "__main__":
    main()
