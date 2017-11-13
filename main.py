#!/usr/bin/env python3

import time
import os
import subprocess

import pynmea2
import crcmod
from bme280 import bme280, bme280_i2c

import py_ublox_i2c.read
import py_ublox_i2c.configure_serial
import utils
import transmitter as transmitter_class
import camera as camera_class

callsign = "RADIOFLYER"

ublox_i2c_address = 0x42 # FIXME should be in lib
BUS = None

crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')

coordinate_precision = 6

operational_packet_template = "{callsign},{seq},{time},{lat},{lon},{alt},{num_sats},{num_gps_reads},{temperature},{pressure},{humidity}"
no_fix_packet_template = "{callsign},{seq},NOFIX,{time},{num_sats},{num_gps_reads},{temperature},{pressure},{humidity},{uptime}"
# TODO: should I send \r\n or can we just all be unix friends from now on?
sentence_template = "$${0}*{1:X}\n"

def configure_ublox():
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure_for_flight()
    utils.disable_relay_uart_to_gps()


def setup_bme280():
    bme280_i2c.set_default_bus(1)
    bme280_i2c.set_default_i2c_address(0x76)
    bme280.setup()

def main():
    sequence = 0
    configure_ublox()
    camera = camera_class.Camera()
    transmitter = transmitter_class.Transmitter()
    transmitter.send("Worlds best tracker software. Buy bitcoin!\n\n")
    transmitter.send("Thanks to my lovely wife Sarah.\n\n")
    py_ublox_i2c.read.connect_bus()
    setup_bme280()
    num_gps_reads = 0
    while True:
        gps_location = None
        try:
            num_gps_reads += 1
            gps_location = py_ublox_i2c.read.read_gps(ublox_i2c_address)
        except py_ublox_i2c.read.BadDataException:
            utils.print_status_char("!")
            time.sleep(0.5)
            continue
        except KeyError:
            utils.print_status_char("K")
        except IOError:
            utils.print_status_char("I")
        except pynmea2.nmea.ParseError:
            utils.print_status_char("P")
        if not gps_location:
            utils.print_status_char(".")
            time.sleep(0.5)
            continue
        bme280_data = bme280.read_all()
        packet_params = {
            'callsign': callsign,
            'seq': sequence,
            'num_gps_reads': num_gps_reads,
            'temperature': round(bme280_data.temperature, 2),
            'humidity': round(bme280_data.humidity, 2),
            'pressure': round(bme280_data.pressure, 2),
        }
        if gps_location.sentence_type == 'GGA':
            timestamp = gps_location.timestamp.isoformat() if gps_location.timestamp else "00:00:00"
            packet_params.update({
                'num_sats': int(gps_location.num_sats),
                'time': timestamp,
            })
            if gps_location.gps_qual == 0:
                packet_template = no_fix_packet_template
                packet_params.update({
                    'uptime': utils.uptime()
                })
            else:
                packet_template = operational_packet_template
                packet_params.update({
                    'alt': int(round(gps_location.altitude, 0)),
                    'lat': round(gps_location.latitude, coordinate_precision), # FIXME: what does dl-fldigi require? see serenity code.
                    'lon': round(gps_location.longitude, coordinate_precision),
                })
        else:
            # Oh shit, the GPS is sending things I don't know how to handle
            crazy = "%s: Unexpected GPS data: %s\n" % (callsign, gps_location)
            transmitter.send(crazy)
            if gps_location.sentence_type in ("GLL", "GSA", "RMC", "GSV", "VTG"):
                # either the initial config of the ublox didn't work, or it's been reset/rebooted.
                # closing the uart should block until it's done spooling data.
                transmitter.send("%s: Re-configuring ublox in 10 seconds.\n" % callsign)
                time.sleep(10)
                transmitter.close_uart()
                print("UART closed, go go go")
                configure_ublox()
                transmitter.open_uart()
            continue
        packet = packet_template.format(**packet_params)
        checksum = crc16f(packet.encode('ascii'))
        sentence = sentence_template.format(packet, checksum)
        print("")
        camera.take_photo(packet_params)
        transmitter.send(sentence)
        num_gps_reads = 0
        sequence += 1


if __name__ == "__main__":
    main()
