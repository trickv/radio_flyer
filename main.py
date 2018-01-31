#!/usr/bin/env python3
""" Main tracker loop """

import time

import crcmod
import lib

import utils

CALLSIGN = "RADIOFLYER"

PACKET_TEMPLATES = {
    'operational': "{callsign},{seq},{time},{lat},{lon},{alt}," +
                   "{num_sats},{temperature},{pressure},{humidity}," +
                   "{internal_temperature}",
    'no_fix': "{callsign},{seq},NOFIX,{time},{num_sats}," +
              "{temperature},{pressure},{humidity},{uptime}," +
              "{internal_temperature}",
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
    transmitter.send("HAB tracker callsign {} starting up.\r\n".format(CALLSIGN))
    transmitter.send("Worlds best tracker software.\r\n")
    transmitter.send("Thanks to my lovely wife Sarah.\r\n")
    gps = lib.Gps()
    bme280_sensor = lib.Bme280()
    lm75_sensor = lib.Lm75()
    crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    transmitter.send("Tracker up and running. Lets fly!\r\n\r\n")

    while True:
        gps_location = None
        gps_location = gps.read()
        if not gps_location:
            utils.print_status_char(".")
            time.sleep(2)
            continue
        bme280_data = bme280_sensor.read()
        packet_params = {
            'callsign': CALLSIGN,
            'seq': sequence,
            'temperature': round(bme280_data.temperature, 2),
            'humidity': round(bme280_data.humidity, 2),
            'pressure': round(bme280_data.pressure, 2),
            'internal_temperature': lm75_sensor.get_temperature(),
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
                'alt': int(round(gps_location.altitude, 0)),
                'lat': round(gps_location.latitude, 6), # FIXME: what does dl-fldigi require? see serenity code.
                'lon': round(gps_location.longitude, 6),
            })
        packet = packet_template.format(**packet_params)
        checksum = crc16f(packet.encode('ascii'))
        sentence = SENTENCE_TEMPLATE.format(packet, checksum)
        if not had_initial_fix:
            transmitter.send("{}: do not launch yet\r\n".format(CALLSIGN))
        transmitter.send(sentence)
        sequence += 1


if __name__ == "__main__":
    main()
