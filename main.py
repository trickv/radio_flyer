#!/usr/bin/env python3
""" Main tracker loop """

import time

import crcmod
import lib

import utils
from conf import CONF as conf

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
SENTENCE_TEMPLATE = "$${0}*{1:04X}\r\n"


def main():
    """ Main tracker loop. Never exits. """
    sequence = 0
    had_initial_fix = False
    transmitter = lib.Transmitter()
    rendered_conf = utils.render_conf(conf)
    print(rendered_conf)
    transmitter.send(rendered_conf)
    transmitter.send("Worlds best tracker software. Buy bitcoin!\r\n\r\n")
    transmitter.send("Thanks to my lovely wife Sarah.\r\n\r\n")
    gps = lib.Gps()
    bme280_sensor = lib.Bme280()
    lm75_sensor = lib.Lm75()
    crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')

    while True:
        gps_location = None
        gps_location = gps.read()
        if not gps_location:
            utils.print_status_char(".")
            time.sleep(2)
            continue
        bme280_data = bme280_sensor.read()
        packet_params = {
            'callsign': conf['callsign'],
            'seq': sequence,
            'temperature': round(bme280_data.temperature, 2),
            'humidity': round(bme280_data.humidity, 2),
            'pressure': round(bme280_data.pressure, 2),
            'internal_temperature': lm75_sensor.get_temperature(),
        }
        if gps_location.sentence_type == 'GGA':
            timestamp = gps_location.timestamp.isoformat() if gps_location.timestamp else "00:00:00"
            packet_params.update({
                'num_sats': int(gps_location.num_sats),
                'time': timestamp,
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
                    'lat': round(gps_location.latitude, conf['coordinate_precision']), # FIXME: what does dl-fldigi require? see serenity code.
                    'lon': round(gps_location.longitude, conf['coordinate_precision']),
                })
        else:
            # Oh shit, the GPS is sending things I don't know how to handle
            # FIXME remove this else, this is all unncessary code! :)
            crazy = "%s: Unexpected GPS data: %s\r\n" % (conf['callsign'], gps_location)
            transmitter.send(crazy)
            if gps_location.sentence_type in ("GLL", "GSA", "RMC", "GSV", "VTG"):
                # either the initial config of the ublox didn't work, or it's been reset/rebooted.
                # closing the uart should block until it's done spooling data.
                transmitter.send("%s: Re-configuring ublox in 10 seconds.\r\n" % conf['callsign'])
                time.sleep(10)
                transmitter.close_uart()
                print("UART closed, go go go")
                #configure_ublox()
                transmitter.open_uart()
            continue
        packet = packet_template.format(**packet_params)
        checksum = crc16f(packet.encode('ascii'))
        sentence = SENTENCE_TEMPLATE.format(packet, checksum)
        print("")
        if not had_initial_fix:
            transmitter.send("%s: do not launch yet\r\n" % conf['callsign'])
        transmitter.send(sentence)
        sequence += 1


if __name__ == "__main__":
    main()
